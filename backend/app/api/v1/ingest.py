"""
Endpoints d'ingestion de corpus (R10 — préfixe /api/v1/).

POST /api/v1/corpora/{id}/ingest/files
POST /api/v1/corpora/{id}/ingest/iiif-manifest
POST /api/v1/corpora/{id}/ingest/iiif-images

Règle (R01) : aucune logique spécifique à un corpus particulier.
Règle : ingestion = création des PageModel en BDD uniquement.
         L'analyse IA est déclenchée séparément via /run.
"""
# 1. stdlib
import logging
import re
import uuid
from pathlib import Path

# 2. third-party
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. local
from app import config as _config_module
from app.models.corpus import CorpusModel, ManuscriptModel, PageModel
from app.models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

# ── Constantes de sécurité ────────────────────────────────────────────────────

_SAFE_LABEL_RE = re.compile(r"^[\w\-\.]+$")
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 Mo par fichier
_ALLOWED_MIME_PREFIXES = ("image/",)


def _sanitize_label(label: str) -> str:
    """Nettoie un folio_label : garde uniquement alphanum, -, _, ."""
    clean = Path(label).name  # retire tout chemin
    if not _SAFE_LABEL_RE.match(clean) or not clean:
        clean = re.sub(r"[^\w\-\.]", "_", clean) or "page"
    return clean


def _sanitize_filename(name: str) -> str:
    """Nettoie un nom de fichier uploadé : garde uniquement le basename sûr."""
    clean = Path(name).name
    if not _SAFE_LABEL_RE.match(clean) or not clean:
        clean = f"{uuid.uuid4().hex[:12]}.bin"
    return clean


# ── Schémas ───────────────────────────────────────────────────────────────────

class IIIFManifestRequest(BaseModel):
    manifest_url: str


class IIIFImagesRequest(BaseModel):
    urls: list[str] = Field(..., max_length=5000)
    folio_labels: list[str] = Field(..., max_length=5000)


class IngestResponse(BaseModel):
    corpus_id: str
    manuscript_id: str
    pages_created: int
    pages_skipped: int = 0
    page_ids: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_corpus_or_404(corpus_id: str, db: AsyncSession) -> CorpusModel:
    corpus = await db.get(CorpusModel, corpus_id)
    if corpus is None:
        raise HTTPException(status_code=404, detail="Corpus introuvable")
    return corpus


async def _get_or_create_manuscript(
    db: AsyncSession, corpus_id: str, title: str | None = None
) -> ManuscriptModel:
    """Retourne le premier manuscrit du corpus, ou en crée un par défaut."""
    result = await db.execute(
        select(ManuscriptModel).where(ManuscriptModel.corpus_id == corpus_id).limit(1)
    )
    ms = result.scalar_one_or_none()
    if ms is not None:
        return ms

    corpus = await db.get(CorpusModel, corpus_id)
    ms = ManuscriptModel(
        id=str(uuid.uuid4()),
        corpus_id=corpus_id,
        title=title or (corpus.title if corpus else corpus_id),
        total_pages=0,
    )
    db.add(ms)
    await db.flush()
    return ms


async def _next_sequence(db: AsyncSession, manuscript_id: str) -> int:
    """Retourne le prochain numéro de séquence disponible (max + 1, ou 1)."""
    result = await db.execute(
        select(func.max(PageModel.sequence)).where(
            PageModel.manuscript_id == manuscript_id
        )
    )
    max_seq = result.scalar_one_or_none()
    return (max_seq or 0) + 1


def _find_duplicate_labels(labels: list[str]) -> set[str]:
    """Retourne les folio_labels qui apparaissent plus d'une fois."""
    seen: dict[str, int] = {}
    for label in labels:
        seen[label] = seen.get(label, 0) + 1
    return {label for label, count in seen.items() if count > 1}


def _make_page_id(corpus_slug: str, folio_label: str, batch_index: int, duplicate_labels: set[str]) -> str:
    """Génère un ID de page.  Ajoute le batch_index si le label n'est pas unique."""
    if folio_label in duplicate_labels:
        return f"{corpus_slug}-{batch_index:04d}-{folio_label}"
    return f"{corpus_slug}-{folio_label}"


async def _create_page(
    db: AsyncSession,
    manuscript_id: str,
    page_id: str,
    folio_label: str,
    sequence: int,
    image_master_path: str | None = None,
) -> PageModel | None:
    """Crée une page si elle n'existe pas déjà.  Retourne None si l'ID est déjà pris."""
    existing = await db.get(PageModel, page_id)
    if existing is not None:
        logger.info("Page déjà existante, ignorée", extra={"page_id": page_id})
        return None

    page = PageModel(
        id=page_id,
        manuscript_id=manuscript_id,
        folio_label=folio_label,
        sequence=sequence,
        image_master_path=image_master_path,
        processing_status="INGESTED",
    )
    db.add(page)
    return page


_MANIFEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ScriptoriumAI/1.0; "
        "+https://huggingface.co/spaces/Ma-Ri-Ba-Ku/scriptorium-ai)"
    ),
    "Accept": "application/ld+json,application/json,*/*",
    "Referer": "https://gallica.bnf.fr/",
}


_MAX_MANIFEST_BYTES = 10 * 1024 * 1024  # 10 Mo max pour un manifest JSON


def _validate_url(url: str) -> None:
    """Rejette les URLs non-HTTP et les cibles réseau privé (SSRF)."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Schéma non autorisé : {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    # Bloquer les adresses privées / locales
    blocked = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal")
    if host in blocked or host.startswith("169.254.") or host.startswith("10.") or host.startswith("192.168."):
        raise ValueError(f"Hôte interdit : {host}")


async def _fetch_json_manifest(url: str) -> dict:
    """Télécharge un manifest IIIF avec protections SSRF + taille max."""
    _validate_url(url)
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_MANIFEST_HEADERS, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        if len(resp.content) > _MAX_MANIFEST_BYTES:
            raise ValueError(f"Manifest trop volumineux ({len(resp.content)} octets)")
        return resp.json()


def _extract_canvas_label(canvas: dict, index: int) -> str:
    """Extrait le folio_label d'un canvas IIIF (3.0 ou 2.x)."""
    label = canvas.get("label")
    if isinstance(label, dict):
        for lang in ("none", "en", "fr", "la"):
            values = label.get(lang)
            if values:
                return (values[0] if isinstance(values, list) else str(values)).strip()
    elif isinstance(label, str) and label.strip():
        return label.strip()
    return f"f{index + 1:03d}r"


def _extract_canvas_image_url(canvas: dict) -> str | None:
    """Extrait l'URL de l'image principale d'un canvas IIIF (3.0 ou 2.x)."""
    # IIIF 3.0
    items = canvas.get("items") or []
    if items:
        ann_items = (items[0].get("items") or []) if items else []
        if ann_items:
            body = ann_items[0].get("body") or {}
            if isinstance(body, dict):
                return body.get("id") or body.get("@id")
    # IIIF 2.x
    images = canvas.get("images") or []
    if images:
        resource = images[0].get("resource") or {}
        return resource.get("@id")
    # Fallback : ID du canvas
    return canvas.get("id") or canvas.get("@id")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/corpora/{corpus_id}/ingest/files", response_model=IngestResponse, status_code=201)
async def ingest_files(
    corpus_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Ingère une liste de fichiers images (multipart/form-data).

    Chaque fichier crée un PageModel. Le fichier est copié dans
    data/corpora/{slug}/masters/{folio_label}/{filename}.
    """
    corpus = await _get_corpus_or_404(corpus_id, db)
    ms = await _get_or_create_manuscript(db, corpus_id)
    seq = await _next_sequence(db, ms.id)

    # Collect labels and detect duplicates
    labels = [_sanitize_label(Path(f.filename or f"file_{i}").stem) for i, f in enumerate(files)]
    dupes = _find_duplicate_labels(labels)

    created: list[PageModel] = []
    written_files: list[Path] = []
    skipped = 0
    for i, upload in enumerate(files):
        # Validation MIME type
        ctype = upload.content_type or ""
        if not any(ctype.startswith(p) for p in _ALLOWED_MIME_PREFIXES):
            raise HTTPException(
                status_code=422,
                detail=f"Type MIME non autorisé : {ctype!r}. Seules les images sont acceptées.",
            )

        filename = _sanitize_filename(upload.filename or f"file_{i}.bin")
        folio_label = labels[i]
        page_id = _make_page_id(corpus.slug, folio_label, seq + i, dupes)

        content = await upload.read()
        # Validation taille
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux ({len(content)} octets). Maximum : {_MAX_UPLOAD_BYTES}.",
            )

        master_dir = (
            _config_module.settings.data_dir
            / "corpora"
            / corpus.slug
            / "masters"
            / folio_label
        )
        master_dir.mkdir(parents=True, exist_ok=True)
        master_path = master_dir / filename
        master_path.write_bytes(content)
        written_files.append(master_path)

        page = await _create_page(
            db, ms.id, page_id, folio_label, seq + i,
            image_master_path=str(master_path),
        )
        if page is None:
            skipped += 1
        else:
            created.append(page)

    ms.total_pages = (ms.total_pages or 0) + len(created)
    try:
        await db.commit()
    except Exception:
        # Nettoyage des fichiers orphelins si le commit BDD échoue
        for f in written_files:
            f.unlink(missing_ok=True)
        raise

    logger.info(
        "Fichiers ingérés",
        extra={"corpus_id": corpus_id, "created": len(created), "skipped": skipped},
    )
    return IngestResponse(
        corpus_id=corpus_id,
        manuscript_id=ms.id,
        pages_created=len(created),
        pages_skipped=skipped,
        page_ids=[p.id for p in created],
    )


@router.post("/corpora/{corpus_id}/ingest/iiif-manifest", response_model=IngestResponse, status_code=201)
async def ingest_iiif_manifest(
    corpus_id: str,
    body: IIIFManifestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Télécharge un manifest IIIF, extrait les canvases et crée les PageModel."""
    corpus = await _get_corpus_or_404(corpus_id, db)

    try:
        manifest = await _fetch_json_manifest(body.manifest_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur HTTP lors du téléchargement du manifest : {exc.response.status_code}",
        )
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur réseau lors du téléchargement du manifest : {exc}",
        )

    # Détecte le format IIIF (3.0 vs 2.x)
    canvases: list[dict] = manifest.get("items") or []
    if not canvases:
        sequences = manifest.get("sequences") or []
        canvases = sequences[0].get("canvases", []) if sequences else []

    if not canvases:
        raise HTTPException(
            status_code=422,
            detail="Le manifest IIIF ne contient aucun canvas (items vide)",
        )

    # Titre du manuscrit depuis le manifest
    ms_title_raw = manifest.get("label") or {}
    if isinstance(ms_title_raw, dict):
        for lang in ("none", "fr", "en"):
            v = ms_title_raw.get(lang)
            if v:
                ms_title = v[0] if isinstance(v, list) else str(v)
                break
        else:
            ms_title = corpus.title
    elif isinstance(ms_title_raw, str):
        ms_title = ms_title_raw
    else:
        ms_title = corpus.title

    ms = await _get_or_create_manuscript(db, corpus_id, title=ms_title)
    seq = await _next_sequence(db, ms.id)

    # Collect labels and detect duplicates
    labels = [_sanitize_label(_extract_canvas_label(canvas, i)) for i, canvas in enumerate(canvases)]
    dupes = _find_duplicate_labels(labels)

    created: list[PageModel] = []
    skipped = 0
    for i, canvas in enumerate(canvases):
        folio_label = labels[i]
        page_id = _make_page_id(corpus.slug, folio_label, seq + i, dupes)
        image_url = _extract_canvas_image_url(canvas)
        page = await _create_page(
            db, ms.id, page_id, folio_label, seq + i,
            image_master_path=image_url,
        )
        if page is None:
            skipped += 1
        else:
            created.append(page)

    ms.total_pages = (ms.total_pages or 0) + len(created)
    await db.commit()

    logger.info(
        "Manifest IIIF ingéré",
        extra={"corpus_id": corpus_id, "url": body.manifest_url, "created": len(created), "skipped": skipped},
    )
    return IngestResponse(
        corpus_id=corpus_id,
        manuscript_id=ms.id,
        pages_created=len(created),
        pages_skipped=skipped,
        page_ids=[p.id for p in created],
    )


@router.post("/corpora/{corpus_id}/ingest/iiif-images", response_model=IngestResponse, status_code=201)
async def ingest_iiif_images(
    corpus_id: str,
    body: IIIFImagesRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Ingère une liste d'URLs d'images IIIF directes.

    urls et folio_labels doivent avoir la même longueur.
    """
    if len(body.urls) != len(body.folio_labels):
        raise HTTPException(
            status_code=422,
            detail=f"urls ({len(body.urls)}) et folio_labels ({len(body.folio_labels)}) doivent avoir la même longueur",
        )
    if not body.urls:
        raise HTTPException(status_code=422, detail="La liste d'URLs est vide")

    corpus = await _get_corpus_or_404(corpus_id, db)
    ms = await _get_or_create_manuscript(db, corpus_id)
    seq = await _next_sequence(db, ms.id)

    sanitized_labels = [_sanitize_label(lbl) for lbl in body.folio_labels]
    dupes = _find_duplicate_labels(sanitized_labels)

    created: list[PageModel] = []
    skipped = 0
    for i, (url, folio_label) in enumerate(zip(body.urls, sanitized_labels)):
        page_id = _make_page_id(corpus.slug, folio_label, seq + i, dupes)
        page = await _create_page(
            db, ms.id, page_id, folio_label, seq + i,
            image_master_path=url,
        )
        if page is None:
            skipped += 1
        else:
            created.append(page)

    ms.total_pages = (ms.total_pages or 0) + len(created)
    await db.commit()

    logger.info(
        "Images IIIF ingérées",
        extra={"corpus_id": corpus_id, "created": len(created), "skipped": skipped},
    )
    return IngestResponse(
        corpus_id=corpus_id,
        manuscript_id=ms.id,
        pages_created=len(created),
        pages_skipped=skipped,
        page_ids=[p.id for p in created],
    )
