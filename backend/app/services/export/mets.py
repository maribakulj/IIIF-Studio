"""
Générateur METS v1.12 depuis une liste de PageMaster (R02).

Source canonique : liste de PageMaster uniquement — jamais les réponses brutes.
Les 6 sections obligatoires : metsHdr, dmdSec, amdSec, fileSec,
structMap PHYSICAL, structMap LOGICAL.

fileSec → 3 fileGrp par manuscrit :
  master        = URL image originale  (master.image["original_url"])
  derivative_web = dérivé JPEG         (master.image["derivative_web"])
  alto           = chemin attendu      (data/corpora/{slug}/pages/{folio}/alto.xml)

structMap PHYSICAL = séquence des pages triées par master.sequence.
structMap LOGICAL  = 1 seul div TYPE="manuscript" (MVP).
"""
# 1. stdlib
import logging
from datetime import datetime, timezone
from pathlib import Path

# 2. third-party
from lxml import etree

# 3. local
from app.schemas.page_master import PageMaster

logger = logging.getLogger(__name__)

# ── Namespaces METS ──────────────────────────────────────────────────────────
_METS_NS   = "http://www.loc.gov/METS/"
_MODS_NS   = "http://www.loc.gov/mods/v3"
_DC_NS     = "http://purl.org/dc/elements/1.1/"
_XLINK_NS  = "http://www.w3.org/1999/xlink"
_XSI_NS    = "http://www.w3.org/2001/XMLSchema-instance"
_SCHEMA_LOC = (
    "http://www.loc.gov/METS/ "
    "https://www.loc.gov/standards/mets/mets.xsd"
)

_M   = f"{{{_METS_NS}}}"
_DC  = f"{{{_DC_NS}}}"
_XL  = f"{{{_XLINK_NS}}}"


def _el(parent: etree._Element, tag: str, attrib: dict | None = None,
        text: str | None = None) -> etree._Element:
    el = etree.SubElement(parent, tag, attrib or {})
    if text is not None:
        el.text = text
    return el


def _safe_id(value: str) -> str:
    """Remplace les caractères non autorisés dans un ID XML par '_'."""
    return value.replace("-", "_").replace(".", "_").replace(" ", "_")


def _alto_path(corpus_slug: str, folio_label: str, base_data_dir: Path) -> str:
    """Retourne le chemin attendu de l'alto.xml pour une page."""
    return str(base_data_dir / "corpora" / corpus_slug / "pages" / folio_label / "alto.xml")


def generate_mets(
    masters: list[PageMaster],
    manuscript_meta: dict,
    base_data_dir: Path = Path("data"),
) -> str:
    """Génère le XML METS v1.12 complet pour un manuscrit.

    Args:
        masters: liste des PageMaster du manuscrit (au moins 1).
        manuscript_meta: dict avec les clés :
            Obligatoires : manuscript_id (str), label (str), corpus_slug (str)
            Optionnelles : language (str), repository (str), shelfmark (str),
                           date_label (str), institution (str)
        base_data_dir: racine du dossier data (pour construire les chemins ALTO).

    Returns:
        Chaîne UTF-8 contenant le XML METS (avec déclaration XML).

    Raises:
        ValueError: si masters est vide ou si un champ obligatoire est absent.
    """
    # ── Validation des entrées ───────────────────────────────────────────────
    if not masters:
        raise ValueError(
            "generate_mets : la liste de PageMaster est vide — "
            "un manuscrit doit avoir au moins une page."
        )
    for key in ("manuscript_id", "label", "corpus_slug"):
        if not manuscript_meta.get(key):
            raise ValueError(
                f"generate_mets : champ obligatoire manquant dans manuscript_meta : «{key}»"
            )

    manuscript_id = manuscript_meta["manuscript_id"]
    label         = manuscript_meta["label"]
    corpus_slug   = manuscript_meta["corpus_slug"]
    language      = manuscript_meta.get("language", "")
    repository    = manuscript_meta.get("repository", "")
    shelfmark     = manuscript_meta.get("shelfmark", "")
    date_label    = manuscript_meta.get("date_label", "")
    institution   = manuscript_meta.get("institution", "")

    # Pages triées par séquence (R02 — structMap PHYSICAL doit respecter sequence)
    pages = sorted(masters, key=lambda m: m.sequence)

    now_iso = datetime.now(tz=timezone.utc).isoformat()

    # ── Racine ──────────────────────────────────────────────────────────────
    nsmap = {
        "mets":  _METS_NS,
        "dc":    _DC_NS,
        "xlink": _XLINK_NS,
        "xsi":   _XSI_NS,
    }
    root = etree.Element(
        f"{_M}mets",
        {
            "OBJID":  manuscript_id,
            "TYPE":   "Manuscript",
            "LABEL":  label,
            f"{{{_XSI_NS}}}schemaLocation": _SCHEMA_LOC,
        },
        nsmap=nsmap,
    )

    # ── 1. metsHdr ──────────────────────────────────────────────────────────
    hdr = _el(root, f"{_M}metsHdr", {"CREATEDATE": now_iso})
    agent = _el(hdr, f"{_M}agent", {"ROLE": "CREATOR", "TYPE": "ORGANIZATION"})
    _el(agent, f"{_M}name", text="IIIF Studio")

    # ── 2. dmdSec — Dublin Core ─────────────────────────────────────────────
    dmd = _el(root, f"{_M}dmdSec", {"ID": "DMD_1"})
    wrap = _el(dmd, f"{_M}mdWrap", {"MDTYPE": "DC"})
    xml_data = _el(wrap, f"{_M}xmlData")

    _el(xml_data, f"{_DC}title",      text=label)
    _el(xml_data, f"{_DC}identifier", text=manuscript_id)
    if language:
        _el(xml_data, f"{_DC}language", text=language)
    if repository:
        _el(xml_data, f"{_DC}source", text=repository)
    if shelfmark:
        _el(xml_data, f"{_DC}relation", text=shelfmark)
    if date_label:
        _el(xml_data, f"{_DC}date", text=date_label)
    if institution:
        _el(xml_data, f"{_DC}publisher", text=institution)
    _el(xml_data, f"{_DC}format", text="application/mets+xml")

    # ── 3. amdSec — techMD global ───────────────────────────────────────────
    amd = _el(root, f"{_M}amdSec")
    tech = _el(amd, f"{_M}techMD", {"ID": "AMD_1"})
    amd_wrap = _el(tech, f"{_M}mdWrap", {"MDTYPE": "OTHER", "OTHERMDTYPE": "IIIFStudio"})
    amd_data = _el(amd_wrap, f"{_M}xmlData")

    # Premier processing trouvé parmi les pages
    first_processing = next(
        (m.processing for m in pages if m.processing is not None), None
    )
    amd_root = etree.SubElement(amd_data, "iiifStudioProcessing")
    _el(amd_root, "generator",   text="IIIF Studio")
    _el(amd_root, "pageCount",   text=str(len(pages)))
    _el(amd_root, "corpusSlug",  text=corpus_slug)
    if first_processing:
        _el(amd_root, "modelId",         text=first_processing.model_id)
        _el(amd_root, "modelDisplayName", text=first_processing.model_display_name)
        _el(amd_root, "processedAt",     text=first_processing.processed_at.isoformat())

    # ── 4. fileSec — 3 fileGrp ──────────────────────────────────────────────
    file_sec = _el(root, f"{_M}fileSec")

    grp_master = _el(file_sec, f"{_M}fileGrp", {"USE": "master"})
    grp_deriv  = _el(file_sec, f"{_M}fileGrp", {"USE": "derivative_web"})
    grp_alto   = _el(file_sec, f"{_M}fileGrp", {"USE": "alto"})

    for page in pages:
        sid = _safe_id(page.page_id)

        # master image
        f_master = _el(grp_master, f"{_M}file", {"ID": f"IMG_MASTER_{sid}", "MIMETYPE": "image/jpeg"})
        _el(f_master, f"{_M}FLocat", {
            "LOCTYPE": "URL",
            f"{_XL}href": page.image.master or "",
            f"{_XL}type": "simple",
        })

        # dérivé web
        f_deriv = _el(grp_deriv, f"{_M}file", {"ID": f"IMG_DERIV_{sid}", "MIMETYPE": "image/jpeg"})
        _el(f_deriv, f"{_M}FLocat", {
            "LOCTYPE": "OTHER",
            "OTHERLOCTYPE": "filepath",
            f"{_XL}href": page.image.derivative_web or "",
            f"{_XL}type": "simple",
        })

        # ALTO (référence conditionnelle — warning si le fichier n'existe pas encore)
        alto_p = _alto_path(corpus_slug, page.folio_label, base_data_dir)
        if not Path(alto_p).exists():
            logger.warning(
                "Fichier ALTO absent — la référence METS sera cassée tant que l'ALTO n'est pas généré",
                extra={"alto_path": alto_p, "page_id": page.page_id},
            )
        f_alto = _el(grp_alto, f"{_M}file", {"ID": f"ALTO_{sid}", "MIMETYPE": "text/xml"})
        _el(f_alto, f"{_M}FLocat", {
            "LOCTYPE": "OTHER",
            "OTHERLOCTYPE": "filepath",
            f"{_XL}href": alto_p,
            f"{_XL}type": "simple",
        })

    # ── 5. structMap PHYSICAL ────────────────────────────────────────────────
    sm_phys = _el(root, f"{_M}structMap", {"TYPE": "PHYSICAL"})
    div_seq = _el(sm_phys, f"{_M}div", {"TYPE": "physSequence", "LABEL": label})

    for page in pages:
        sid = _safe_id(page.page_id)
        div_page = _el(div_seq, f"{_M}div", {
            "TYPE":       "page",
            "ORDER":      str(page.sequence),
            "ORDERLABEL": page.folio_label,
            "LABEL":      f"Folio {page.folio_label}",
            "DMDID":      "DMD_1",
        })
        _el(div_page, f"{_M}fptr", {"FILEID": f"IMG_MASTER_{sid}"})
        _el(div_page, f"{_M}fptr", {"FILEID": f"IMG_DERIV_{sid}"})
        _el(div_page, f"{_M}fptr", {"FILEID": f"ALTO_{sid}"})

    # ── 6. structMap LOGICAL ─────────────────────────────────────────────────
    sm_log = _el(root, f"{_M}structMap", {"TYPE": "LOGICAL"})
    _el(sm_log, f"{_M}div", {
        "TYPE":  "manuscript",
        "LABEL": label,
        "DMDID": "DMD_1",
    })

    logger.info(
        "METS généré",
        extra={"manuscript_id": manuscript_id, "pages": len(pages)},
    )

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


def write_mets(
    mets_xml: str,
    corpus_slug: str,
    base_data_dir: Path = Path("data"),
) -> None:
    """Écrit le XML METS dans data/corpora/{corpus_slug}/mets.xml.

    Crée les dossiers parents si nécessaire.

    Args:
        mets_xml: chaîne XML retournée par generate_mets().
        corpus_slug: identifiant du corpus (détermine le répertoire de sortie).
        base_data_dir: racine du dossier data.
    """
    output_path = base_data_dir / "corpora" / corpus_slug / "mets.xml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mets_xml, encoding="utf-8")
    logger.info("mets.xml écrit", extra={"path": str(output_path)})
