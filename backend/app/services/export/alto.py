"""
Générateur ALTO v4 depuis un PageMaster validé (R02).

Source canonique : PageMaster uniquement — jamais la réponse brute ai_raw.json.
bbox [x, y, width, height] → HPOS / VPOS / WIDTH / HEIGHT (correspondance directe).

Mapping RegionType → élément ALTO :
  text_block / margin / rubric  →  TextBlock
  miniature / decorated_initial →  Illustration
  other                         →  ComposedBlock
"""
# 1. stdlib
import logging
from pathlib import Path

# 2. third-party
from lxml import etree
from pydantic import ValidationError

# 3. local
from app.schemas.page_master import OCRResult, PageMaster, Region, RegionType

logger = logging.getLogger(__name__)

# ── Namespaces ALTO v4 ──────────────────────────────────────────────────────
_ALTO_NS = "http://www.loc.gov/standards/alto/ns-v4#"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_SCHEMA_LOC = (
    "http://www.loc.gov/standards/alto/ns-v4# "
    "https://www.loc.gov/standards/alto/v4/alto-4-2.xsd"
)

# ── Classification des types de régions ─────────────────────────────────────
_TEXT_REGION_TYPES = {RegionType.TEXT_BLOCK, RegionType.MARGIN, RegionType.RUBRIC}
_ILLUSTRATION_TYPES = {RegionType.MINIATURE, RegionType.DECORATED_INITIAL}
_COMPOSED_TYPES = {RegionType.OTHER}


def _a(tag: str) -> str:
    """Retourne le tag qualifié dans le namespace ALTO."""
    return f"{{{_ALTO_NS}}}{tag}"


def _bbox_attrib(region: Region) -> dict[str, str]:
    """Retourne les attributs ALTO bbox depuis une Region (R03 → direct mapping)."""
    x, y, w, h = region.bbox
    return {"HPOS": str(x), "VPOS": str(y), "WIDTH": str(w), "HEIGHT": str(h)}


def _build_text_block(
    parent: etree._Element,
    region: Region,
    ocr_block: dict | None,
    fallback_text: str,
    language: str,
    confidence: float,
) -> None:
    """Ajoute un élément TextBlock au parent.

    Si un bloc OCR est disponible pour cette région ou si fallback_text est fourni,
    ajoute un TextLine / String enfant. Sinon, le TextBlock reste vide (valide ALTO).
    """
    attrib = {"ID": region.id, "LANG": language, **_bbox_attrib(region)}
    block_el = etree.SubElement(parent, _a("TextBlock"), attrib)

    # Résolution du texte pour ce bloc
    text = ""
    block_confidence = confidence

    if ocr_block:
        text = (
            ocr_block.get("text")
            or ocr_block.get("diplomatic_text")
            or ""
        )
        if not text and ocr_block.get("lines"):
            text = " ".join(
                ln.get("text", "") for ln in ocr_block["lines"] if ln.get("text")
            )
        block_confidence = float(ocr_block.get("confidence", confidence))
    elif fallback_text:
        text = fallback_text

    if not text:
        return  # TextBlock sans TextLine — valide ALTO, région visible dans le layout

    x, y, w, h = region.bbox
    line_el = etree.SubElement(
        block_el,
        _a("TextLine"),
        {"ID": f"{region.id}_l1", "HPOS": str(x), "VPOS": str(y), "WIDTH": str(w), "HEIGHT": str(h)},
    )
    etree.SubElement(
        line_el,
        _a("String"),
        {
            "ID": f"{region.id}_l1_s1",
            "CONTENT": text,
            "HPOS": str(x),
            "VPOS": str(y),
            "WIDTH": str(w),
            "HEIGHT": str(h),
            "WC": f"{block_confidence:.4f}",
        },
    )


def generate_alto(master: PageMaster) -> str:
    """Génère le XML ALTO v4 complet depuis un PageMaster.

    Toutes les régions du layout sont validées avant la génération.
    Un master.json avec une région invalide lève une ValueError explicite —
    jamais d'ALTO partiel silencieux.

    Args:
        master: PageMaster Pydantic validé (source canonique, R02).

    Returns:
        Chaîne UTF-8 contenant le XML ALTO v4 (avec déclaration XML).

    Raises:
        ValueError: si une région du layout est invalide (bbox incorrecte, champ manquant).
    """
    # ── 1. Validation stricte de toutes les régions ─────────────────────────
    raw_regions: list[dict] = (master.layout.get("regions") or [])
    regions: list[Region] = []
    for i, raw in enumerate(raw_regions):
        try:
            regions.append(Region.model_validate(raw))
        except (ValidationError, Exception) as exc:
            raise ValueError(
                f"Région [{i}] invalide dans le layout de la page «{master.page_id}» : {exc}"
            ) from exc

    # ── 2. Index OCR par region_id ──────────────────────────────────────────
    ocr: OCRResult | None = master.ocr
    language = (ocr.language if ocr else "la") or "la"
    global_confidence = ocr.confidence if ocr else 0.0
    global_text = (ocr.diplomatic_text if ocr else "") or ""

    ocr_by_region: dict[str, dict] = {}
    if ocr:
        for block in ocr.blocks:
            rid = block.get("region_id")
            if rid:
                ocr_by_region[rid] = block

    # Fallback : si aucun bloc OCR n'est référencé par region_id,
    # le texte diplomatique global ira dans le premier TextBlock.
    has_per_region_ocr = bool(ocr_by_region)
    first_text_block_done = False

    # ── 3. Construction de l'arbre XML ─────────────────────────────────────
    nsmap = {None: _ALTO_NS, "xsi": _XSI_NS}
    root = etree.Element(_a("alto"), nsmap=nsmap)
    root.set(f"{{{_XSI_NS}}}schemaLocation", _SCHEMA_LOC)

    # ── Description ────────────────────────────────────────────────────────
    desc = etree.SubElement(root, _a("Description"))
    etree.SubElement(desc, _a("MeasurementUnit")).text = "pixel"

    src_info = etree.SubElement(desc, _a("sourceImageInformation"))
    file_name = master.image.master or master.image.derivative_web or master.page_id
    etree.SubElement(src_info, _a("fileName")).text = str(file_name)

    if master.processing:
        ocr_proc = etree.SubElement(desc, _a("OCRProcessing"), {"ID": "OCR_1"})
        step = etree.SubElement(ocr_proc, _a("ocrProcessingStep"))
        etree.SubElement(step, _a("processingDateTime")).text = (
            master.processing.processed_at.isoformat()
        )
        software = etree.SubElement(step, _a("processingSoftware"))
        etree.SubElement(software, _a("softwareCreator")).text = "Scriptorium AI"
        etree.SubElement(software, _a("softwareName")).text = (
            master.processing.model_display_name
        )
        etree.SubElement(software, _a("softwareVersion")).text = (
            master.processing.prompt_version
        )

    # ── Layout ─────────────────────────────────────────────────────────────
    layout_el = etree.SubElement(root, _a("Layout"))

    width = master.image.width
    height = master.image.height

    page_id_safe = master.page_id.replace(" ", "_")
    page_el = etree.SubElement(
        layout_el,
        _a("Page"),
        {
            "ID": f"P_{page_id_safe}",
            "PHYSICAL_IMG_NR": str(master.sequence),
            "WIDTH": str(width),
            "HEIGHT": str(height),
        },
    )
    print_space = etree.SubElement(
        page_el,
        _a("PrintSpace"),
        {"HPOS": "0", "VPOS": "0", "WIDTH": str(width), "HEIGHT": str(height)},
    )

    # ── Régions ────────────────────────────────────────────────────────────
    for region in regions:
        if region.type in _TEXT_REGION_TYPES:
            ocr_block = ocr_by_region.get(region.id)
            fallback = ""
            if not has_per_region_ocr and not first_text_block_done and global_text:
                fallback = global_text
                first_text_block_done = True

            _build_text_block(
                print_space,
                region,
                ocr_block=ocr_block,
                fallback_text=fallback,
                language=language,
                confidence=global_confidence,
            )

        elif region.type in _ILLUSTRATION_TYPES:
            etree.SubElement(
                print_space,
                _a("Illustration"),
                {
                    "ID": region.id,
                    "TYPE": region.type.value,
                    **_bbox_attrib(region),
                },
            )

        else:  # _COMPOSED_TYPES (other)
            etree.SubElement(
                print_space,
                _a("ComposedBlock"),
                {"ID": region.id, **_bbox_attrib(region)},
            )

    logger.info(
        "ALTO généré",
        extra={
            "page_id": master.page_id,
            "regions": len(regions),
        },
    )

    # ── 4. Sérialisation ───────────────────────────────────────────────────
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


def write_alto(alto_xml: str, output_path: Path) -> None:
    """Écrit le XML ALTO dans le fichier de sortie.

    Crée les dossiers parents si nécessaire.

    Args:
        alto_xml: chaîne XML retournée par generate_alto().
        output_path: chemin de sortie (typiquement .../pages/{folio}/alto.xml).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(alto_xml, encoding="utf-8")
    logger.info("alto.xml écrit", extra={"path": str(output_path)})
