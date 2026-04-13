"""
Analyse primaire IA d'un folio : appel provider IA + écriture master.json (R02, R04, R05).

Point d'entrée : run_primary_analysis().
Chaîne : prompt_loader → model_registry → provider.generate_content → master_writer → response_parser.
"""
# 1. stdlib
import logging
from datetime import datetime, timezone
from pathlib import Path

# 3. local
from app.schemas.corpus_profile import CorpusProfile
from app.schemas.image import ImageDerivativeInfo, ImageSourceInfo
from app.schemas.model_config import ModelConfig
from app.schemas.page_master import EditorialInfo, EditorialStatus, ImageInfo, PageMaster, ProcessingInfo
from app.services.ai.master_writer import write_ai_raw, write_master_json
from app.services.ai.model_registry import get_provider
from app.services.ai.prompt_loader import load_and_render_prompt
from app.services.ai.response_parser import ParseError, parse_ai_response  # noqa: F401

logger = logging.getLogger(__name__)


def _scale_bbox_coordinates(layout: dict, scale_x: float, scale_y: float) -> dict:
    """Met à l'échelle les bbox de l'espace dérivé vers l'espace canvas original.

    L'IA analyse un dérivé 1500px mais les coordonnées dans master.json
    doivent être en pixels absolus du canvas original (convention IIIF).
    """
    if abs(scale_x - 1.0) < 0.01 and abs(scale_y - 1.0) < 0.01:
        return layout  # pas de scaling nécessaire

    regions = layout.get("regions", [])
    for region in regions:
        bbox = region.get("bbox")
        if bbox and len(bbox) == 4:
            region["bbox"] = [
                round(bbox[0] * scale_x),
                round(bbox[1] * scale_y),
                round(bbox[2] * scale_x),
                round(bbox[3] * scale_y),
            ]
    return layout


def run_primary_analysis(
    *,
    derivative_image_bytes: bytes | None = None,
    derivative_image_path: Path | None = None,
    corpus_profile: CorpusProfile,
    model_config: ModelConfig,
    page_id: str,
    manuscript_id: str,
    corpus_slug: str,
    folio_label: str,
    sequence: int,
    image_info: ImageDerivativeInfo | ImageSourceInfo,
    derivative_width: int | None = None,
    derivative_height: int | None = None,
    base_data_dir: Path = Path("data"),
    project_root: Path = Path("."),
) -> PageMaster:
    """Analyse primaire d'un folio : charge le prompt, appelle l'IA, écrit les fichiers.

    Supporte deux modes :
    - IIIF natif : derivative_image_bytes fourni (bytes en RAM, jamais sur disque)
    - Legacy : derivative_image_path fourni (chemin fichier sur disque)

    Respecte R05 : ai_raw.json toujours écrit en premier.

    Si les dimensions originales (canvas) diffèrent du dérivé, les bbox sont
    mises à l'échelle de l'espace dérivé vers l'espace canvas original.
    """
    # ── Chemins de sortie ───────────────────────────────────────────────────
    page_dir = base_data_dir / "corpora" / corpus_slug / "pages" / folio_label
    raw_path = page_dir / "ai_raw.json"
    master_path = page_dir / "master.json"

    # ── 1. Chargement et rendu du prompt (R04) ──────────────────────────────
    prompt_rel_path: str = corpus_profile.prompt_templates["primary"]
    prompt_abs_path = project_root / prompt_rel_path

    context = {
        "profile_label": corpus_profile.label,
        "language_hints": ", ".join(corpus_profile.language_hints),
        "primary_language": corpus_profile.language_hints[0] if corpus_profile.language_hints else "la",
        "script_type": corpus_profile.script_type.value,
    }
    prompt_text = load_and_render_prompt(prompt_abs_path, context)
    logger.info(
        "Prompt rendu",
        extra={"template": prompt_rel_path, "corpus": corpus_slug, "folio": folio_label},
    )

    # ── 2. Obtention des bytes image ────────────────────────────────────────
    if derivative_image_bytes is not None:
        jpeg_bytes = derivative_image_bytes
    elif derivative_image_path is not None:
        if not derivative_image_path.exists():
            raise FileNotFoundError(f"Image dérivée introuvable : {derivative_image_path}")
        try:
            jpeg_bytes = derivative_image_path.read_bytes()
        except OSError as exc:
            raise RuntimeError(f"Erreur lecture image {derivative_image_path} : {exc}") from exc
    else:
        raise ValueError("Il faut fournir derivative_image_bytes ou derivative_image_path")

    # ── 3. Appel IA via le provider sélectionné ─────────────────────────────
    provider = get_provider(model_config.provider)
    logger.info(
        "Appel IA",
        extra={
            "provider": model_config.provider.value,
            "model": model_config.selected_model_id,
            "corpus": corpus_slug,
            "folio": folio_label,
        },
    )
    raw_text = provider.generate_content(
        image_bytes=jpeg_bytes,
        prompt=prompt_text,
        model_id=model_config.selected_model_id,
    )

    # ── 4. Écriture ai_raw.json TOUJOURS EN PREMIER (R05) ─────────────────
    write_ai_raw(raw_text, raw_path)

    # ── 5. Parsing + validation (ParseError si JSON invalide) ───────────────
    layout, ocr = parse_ai_response(raw_text)

    # ── 5b. Scaling bbox si les dimensions originales diffèrent du dérivé ──
    is_iiif_source = isinstance(image_info, ImageSourceInfo)
    original_w = image_info.original_width
    original_h = image_info.original_height
    deriv_w = derivative_width or (getattr(image_info, "derivative_width", None)) or original_w
    deriv_h = derivative_height or (getattr(image_info, "derivative_height", None)) or original_h

    if original_w > 0 and deriv_w > 0 and (original_w != deriv_w or original_h != deriv_h):
        scale_x = original_w / deriv_w
        scale_y = original_h / deriv_h
        layout = _scale_bbox_coordinates(layout, scale_x, scale_y)

    # ── 6. Construction du PageMaster ───────────────────────────────────────
    processed_at = datetime.now(tz=timezone.utc)

    if is_iiif_source:
        image_block = ImageInfo(
            master=image_info.original_url,
            iiif_service_url=image_info.iiif_service_url,
            manifest_url=image_info.manifest_url,
            width=original_w,
            height=original_h,
        )
    else:
        image_block = ImageInfo(
            master=image_info.original_url,
            derivative_web=getattr(image_info, "derivative_path", None),
            thumbnail=getattr(image_info, "thumbnail_path", None),
            width=original_w,
            height=original_h,
        )

    page_master = PageMaster(
        page_id=page_id,
        corpus_profile=corpus_profile.profile_id,
        manuscript_id=manuscript_id,
        folio_label=folio_label,
        sequence=sequence,
        image=image_block,
        layout=layout,
        ocr=ocr,
        processing=ProcessingInfo(
            provider=model_config.provider.value if hasattr(model_config.provider, "value") else str(model_config.provider),
            model_id=model_config.selected_model_id,
            model_display_name=model_config.selected_model_display_name,
            prompt_version=prompt_rel_path,
            raw_response_path=str(raw_path),
            processed_at=processed_at,
        ),
        editorial=EditorialInfo(status=EditorialStatus.MACHINE_DRAFT),
    )

    # ── 7. Écriture master.json (seulement si parsing OK) ───────────────────
    write_master_json(page_master, master_path)

    logger.info(
        "Analyse primaire terminée",
        extra={
            "page_id": page_id,
            "corpus": corpus_slug,
            "folio": folio_label,
            "regions": len(layout.get("regions", [])),
            "iiif_native": is_iiif_source,
        },
    )
    return page_master
