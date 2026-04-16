"""
Service d'indexation et de recherche pour les pages analysées.

Utilise une colonne normalized_text pré-calculée pour permettre des
recherches SQL LIKE insensibles aux accents, sans charger toutes les
lignes en Python.
"""
import logging
import unicodedata

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.page_search import PageSearchIndex
from app.schemas.page_master import PageMaster

logger = logging.getLogger(__name__)


def _normalize(txt: str) -> str:
    """Minuscules + suppression des accents (NFD -> ASCII)."""
    nfd = unicodedata.normalize("NFD", txt.lower())
    return nfd.encode("ascii", "ignore").decode("ascii")


def _extract_tags(master: PageMaster) -> str:
    """Extrait les tags iconography en une chaine plate."""
    extensions = master.extensions or {}
    icono = extensions.get("iconography") or []
    tags: list[str] = []
    if isinstance(icono, list):
        for item in icono:
            if isinstance(item, dict):
                for t in (item.get("tags") or []):
                    tags.append(str(t))
    return " ".join(tags)


def _build_normalized_text(diplomatic: str, translation: str, tags: str) -> str:
    """Construit le texte normalise concatene pour l'indexation SQL."""
    return _normalize(f"{diplomatic} {translation} {tags}")


async def index_page(db: AsyncSession, master: PageMaster) -> None:
    """Indexe ou met a jour une page dans la table de recherche."""
    existing = await db.get(PageSearchIndex, master.page_id)

    diplomatic = (master.ocr.diplomatic_text if master.ocr else "") or ""
    translation = (master.translation.fr if master.translation else "") or ""
    tags = _extract_tags(master)
    normalized = _build_normalized_text(diplomatic, translation, tags)

    if existing:
        existing.corpus_profile = master.corpus_profile
        existing.manuscript_id = master.manuscript_id
        existing.folio_label = master.folio_label
        existing.diplomatic_text = diplomatic
        existing.translation_fr = translation
        existing.tags = tags
        existing.normalized_text = normalized
    else:
        entry = PageSearchIndex(
            page_id=master.page_id,
            corpus_profile=master.corpus_profile,
            manuscript_id=master.manuscript_id,
            folio_label=master.folio_label,
            diplomatic_text=diplomatic,
            translation_fr=translation,
            tags=tags,
            normalized_text=normalized,
        )
        db.add(entry)

    await db.flush()
    logger.debug("Page indexee", extra={"page_id": master.page_id})


async def search_pages(db: AsyncSession, query: str, limit: int = 200) -> list[dict]:
    """Recherche plein texte dans l'index via SQL LIKE sur normalized_text.

    La colonne normalized_text est pre-calculee a l'indexation (minuscules,
    sans accents). Le filtrage est fait cote SQL, pas en Python.
    """
    query_norm = _normalize(query.strip())
    if not query_norm:
        return []

    # Escape SQL LIKE special characters
    query_escaped = query_norm.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = f"%{query_escaped}%"

    result = await db.execute(
        text("""
            SELECT page_id, corpus_profile, manuscript_id, folio_label,
                   diplomatic_text, translation_fr, tags
            FROM page_search
            WHERE normalized_text LIKE :pattern ESCAPE '\\'
        """),
        {"pattern": like_pattern},
    )
    rows = result.fetchall()

    # Score matching rows in Python (only the filtered subset, not all rows)
    hits: list[dict] = []
    for row in rows:
        page_id, corpus_profile, manuscript_id, folio_label, diplo, trans, tags = row

        score = 0
        excerpt = ""
        for field_text in [diplo, trans, tags]:
            if not field_text:
                continue
            normalized = _normalize(field_text)
            count = normalized.count(query_norm)
            if count > 0:
                score += count
                if not excerpt:
                    idx = normalized.find(query_norm)
                    start = max(0, idx - 60)
                    end = min(len(field_text), idx + len(query_norm) + 60)
                    ex = field_text[start:end]
                    if start > 0:
                        ex = "\u2026" + ex
                    if end < len(field_text):
                        ex = ex + "\u2026"
                    excerpt = ex

        hits.append({
            "page_id": page_id,
            "folio_label": folio_label,
            "manuscript_id": manuscript_id,
            "excerpt": excerpt,
            "score": score,
            "corpus_profile": corpus_profile,
        })

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


async def reindex_all(db: AsyncSession, data_dir) -> int:
    """Reconstruit l'index complet depuis les fichiers master.json existants."""
    import json
    from pathlib import Path

    count = 0
    data_path = Path(data_dir)
    for master_path in data_path.glob("corpora/*/pages/*/master.json"):
        try:
            raw = json.loads(master_path.read_text(encoding="utf-8"))
            if not isinstance(raw.get("page_id"), str):
                continue
            master = PageMaster.model_validate(raw)
            await index_page(db, master)
            count += 1
        except Exception as exc:
            logger.warning("Reindexation echouee pour %s: %s", master_path, exc)
            continue

    await db.commit()
    logger.info("Reindexation terminee", extra={"pages_indexed": count})
    return count
