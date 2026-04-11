"""
Tests du générateur METS v1.12 (Sprint 3 — Session B).

Vérifie :
- XML produit est valide (parseable par lxml)
- 6 sections obligatoires présentes : metsHdr, dmdSec, amdSec, fileSec,
  structMap PHYSICAL, structMap LOGICAL
- fileSec : 3 fileGrp (master, derivative_web, alto), 3 fichiers par page
- structMap PHYSICAL : ordre respecte PageMaster.sequence (pas l'ordre de la liste)
- structMap LOGICAL : 1 seul div TYPE="manuscript"
- Chemins ALTO construits depuis corpus_slug + folio_label
- Métadonnées Dublin Core présentes dans dmdSec
- amdSec : techMD global avec model_id du premier master.processing
- manuscript_id, label, corpus_slug obligatoires → ValueError sinon
- Liste vide → ValueError explicite
- Scénarios réalistes : Beatus HR + BR (1 manuscrit), Grandes Chroniques (autre)
"""
# 1. stdlib
import json
from datetime import datetime, timezone
from pathlib import Path

# 2. third-party
import pytest
from lxml import etree

# 3. local
from app.schemas.page_master import EditorialInfo, EditorialStatus, OCRResult, PageMaster, ProcessingInfo
from app.services.export.mets import generate_mets, write_mets

# ── Namespaces ────────────────────────────────────────────────────────────────
_METS_NS  = "http://www.loc.gov/METS/"
_DC_NS    = "http://purl.org/dc/elements/1.1/"
_XLINK_NS = "http://www.w3.org/1999/xlink"

_NS = {"m": _METS_NS, "dc": _DC_NS, "xlink": _XLINK_NS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(xml_str: str) -> etree._Element:
    return etree.fromstring(xml_str.encode("utf-8"))


def _xp(root: etree._Element, path: str) -> list:
    return root.xpath(path, namespaces=_NS)


def _one(root: etree._Element, path: str) -> etree._Element:
    results = _xp(root, path)
    assert len(results) == 1, f"Expected 1 for {path!r}, got {len(results)}: {results}"
    return results[0]


def _make_page(
    page_id: str,
    folio_label: str,
    sequence: int,
    original_url: str = "",
    derivative_web: str = "",
    with_processing: bool = False,
    ocr_text: str = "",
) -> PageMaster:
    processing = None
    if with_processing:
        processing = ProcessingInfo(
            provider="google_ai_studio",
            model_id="gemini-2.0-flash",
            model_display_name="Gemini 2.0 Flash",
            prompt_version="prompts/medieval-illuminated/primary_v1.txt",
            raw_response_path=f"/data/corpora/test/pages/{folio_label}/ai_raw.json",
            processed_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
    ocr = OCRResult(diplomatic_text=ocr_text, language="la", confidence=0.90) if ocr_text else None
    return PageMaster(
        page_id=page_id,
        corpus_profile="medieval-illuminated",
        manuscript_id="ms-test",
        folio_label=folio_label,
        sequence=sequence,
        image={
            "master": original_url or f"https://example.com/{folio_label}.jpg",
            "derivative_web": derivative_web or f"/data/deriv/{folio_label}.jpg",
            "thumbnail": f"/data/thumb/{folio_label}.jpg",
            "width": 1500,
            "height": 2000,
        },
        layout={"regions": []},
        ocr=ocr,
        processing=processing,
        editorial=EditorialInfo(status=EditorialStatus.MACHINE_DRAFT),
    )


def _base_meta(corpus_slug: str = "test-ms", label: str = "Test Manuscript") -> dict:
    return {
        "manuscript_id": "ms-test-001",
        "label": label,
        "corpus_slug": corpus_slug,
    }


# ── Fixtures réalistes (3 PageMaster du Sprint 2) ───────────────────────────

@pytest.fixture
def beatus_pages():
    """2 pages du Beatus (HR + BR) — même manuscrit, 2 folios."""
    return [
        _make_page(
            page_id="beatus-lat8878-hr-f233",
            folio_label="f233-hr",
            sequence=233,
            original_url="https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/full/0/native.jpg",
            derivative_web="/data/corpora/beatus-lat8878/derivatives/f233-hr.jpg",
            with_processing=True,
            ocr_text="Incipit explanatio",
        ),
        _make_page(
            page_id="beatus-lat8878-br-f233",
            folio_label="f233-br",
            sequence=234,
            original_url="https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/600,/0/native.jpg",
            derivative_web="/data/corpora/beatus-lat8878/derivatives/f233-br.jpg",
            with_processing=False,
        ),
    ]


@pytest.fixture
def beatus_meta():
    return {
        "manuscript_id": "BnF-Latin-8878",
        "label": "Beatus de Saint-Sever",
        "corpus_slug": "beatus-lat8878",
        "language": "la",
        "repository": "Bibliothèque nationale de France",
        "shelfmark": "Latin 8878",
        "date_label": "XIe siècle",
        "institution": "BnF",
    }


@pytest.fixture
def chroniques_pages():
    return [
        _make_page(
            page_id="chroniques-btv1b84472995-f16",
            folio_label="f16",
            sequence=16,
            original_url="https://gallica.bnf.fr/iiif/ark:/12148/btv1b84472995/f16/full/full/0/native.jpg",
            derivative_web="/data/corpora/grandes-chroniques/derivatives/f16.jpg",
            with_processing=True,
            ocr_text="Cy commence le prologue",
        ),
    ]


@pytest.fixture
def chroniques_meta():
    return {
        "manuscript_id": "BnF-btv1b84472995",
        "label": "Grandes Chroniques de France",
        "corpus_slug": "grandes-chroniques",
        "language": "fr",
        "repository": "Bibliothèque nationale de France",
    }


# ---------------------------------------------------------------------------
# Tests — validité XML
# ---------------------------------------------------------------------------

def test_generate_mets_returns_string(beatus_pages, beatus_meta):
    result = generate_mets(beatus_pages, beatus_meta)
    assert isinstance(result, str)


def test_generate_mets_valid_xml(beatus_pages, beatus_meta):
    xml_str = generate_mets(beatus_pages, beatus_meta)
    root = _parse(xml_str)
    assert root is not None


def test_generate_mets_xml_declaration(beatus_pages, beatus_meta):
    xml_str = generate_mets(beatus_pages, beatus_meta)
    assert xml_str.startswith("<?xml")


def test_generate_mets_namespace(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    assert root.tag == f"{{{_METS_NS}}}mets"


def test_generate_mets_objid(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    objid = root.get("OBJID")
    assert objid is not None, "OBJID attribute absent du root mets"
    assert objid == "BnF-Latin-8878"


def test_generate_mets_label(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    assert root.get("LABEL") == "Beatus de Saint-Sever"


def test_generate_mets_type_manuscript(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    assert root.get("TYPE") == "Manuscript"


# ---------------------------------------------------------------------------
# Tests — 6 sections obligatoires présentes
# ---------------------------------------------------------------------------

def test_mets_has_metsHdr(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:metsHdr")


def test_mets_has_dmdSec(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:dmdSec")


def test_mets_has_amdSec(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:amdSec")


def test_mets_has_fileSec(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:fileSec")


def test_mets_has_structMap_physical(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:structMap[@TYPE='PHYSICAL']")


def test_mets_has_structMap_logical(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:structMap[@TYPE='LOGICAL']")


# ---------------------------------------------------------------------------
# Tests — metsHdr
# ---------------------------------------------------------------------------

def test_metsHdr_agent_creator(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    agent = _one(root, "m:metsHdr/m:agent[@ROLE='CREATOR']")
    name = _one(agent, "m:name")
    assert name.text == "IIIF Studio"


def test_metsHdr_has_createdate(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    hdr = _one(root, "m:metsHdr")
    assert hdr.get("CREATEDATE") is not None


# ---------------------------------------------------------------------------
# Tests — dmdSec (Dublin Core)
# ---------------------------------------------------------------------------

def test_dmdSec_has_DC_title(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    title = _one(root, "m:dmdSec//dc:title")
    assert title.text == "Beatus de Saint-Sever"


def test_dmdSec_has_DC_identifier(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    ident = _one(root, "m:dmdSec//dc:identifier")
    assert ident.text == "BnF-Latin-8878"


def test_dmdSec_has_DC_language(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    lang = _one(root, "m:dmdSec//dc:language")
    assert lang.text == "la"


def test_dmdSec_optional_fields(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    # repository → dc:source
    source = _one(root, "m:dmdSec//dc:source")
    assert "nationale de France" in source.text
    # date_label → dc:date
    date = _one(root, "m:dmdSec//dc:date")
    assert "XIe" in date.text


def test_dmdSec_no_optional_fields_when_absent():
    pages = [_make_page("ms-0001r", "0001r", 1)]
    meta = {"manuscript_id": "ms-001", "label": "Test", "corpus_slug": "test"}
    root = _parse(generate_mets(pages, meta))
    # aucun dc:language si non fourni
    assert len(_xp(root, "m:dmdSec//dc:language")) == 0


def test_dmdSec_mdtype_is_dc(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    wrap = _one(root, "m:dmdSec/m:mdWrap")
    assert wrap.get("MDTYPE") == "DC"


# ---------------------------------------------------------------------------
# Tests — amdSec (techMD global)
# ---------------------------------------------------------------------------

def test_amdSec_has_techMD(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    _one(root, "m:amdSec/m:techMD")


def test_amdSec_techMD_contains_model_id(beatus_pages, beatus_meta):
    """model_id du premier master.processing apparaît dans amdSec."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    # Cherche dans le contenu XML libre du techMD
    amd_xml = etree.tostring(
        _one(root, "m:amdSec"), encoding="unicode"
    )
    assert "gemini-2.0-flash" in amd_xml


def test_amdSec_techMD_page_count(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    amd_xml = etree.tostring(_one(root, "m:amdSec"), encoding="unicode")
    assert "2" in amd_xml  # 2 pages


def test_amdSec_techMD_no_processing_still_present():
    """amdSec doit être présent même sans master.processing."""
    pages = [_make_page("ms-0001r", "0001r", 1, with_processing=False)]
    meta = {"manuscript_id": "ms-001", "label": "Test", "corpus_slug": "test"}
    root = _parse(generate_mets(pages, meta))
    _one(root, "m:amdSec/m:techMD")


# ---------------------------------------------------------------------------
# Tests — fileSec (3 fileGrp, 3 fichiers par page)
# ---------------------------------------------------------------------------

def test_fileSec_has_three_fileGrp(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    grps = _xp(root, "m:fileSec/m:fileGrp")
    assert len(grps) == 3


def test_fileSec_fileGrp_USE_values(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    uses = {el.get("USE") for el in _xp(root, "m:fileSec/m:fileGrp")}
    assert uses == {"master", "derivative_web", "alto"}


def test_fileSec_master_fileGrp_count(beatus_pages, beatus_meta):
    """2 pages → 2 fichiers dans le fileGrp master."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    files = _xp(root, "m:fileSec/m:fileGrp[@USE='master']/m:file")
    assert len(files) == 2


def test_fileSec_derivative_fileGrp_count(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    files = _xp(root, "m:fileSec/m:fileGrp[@USE='derivative_web']/m:file")
    assert len(files) == 2


def test_fileSec_alto_fileGrp_count(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    files = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file")
    assert len(files) == 2


def test_fileSec_master_url_is_original_url(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='master']/m:file/m:FLocat")
    hrefs = {el.get(f"{{{_XLINK_NS}}}href") for el in flocats}
    assert "https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/full/0/native.jpg" in hrefs
    assert "https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/600,/0/native.jpg" in hrefs


def test_fileSec_master_loctype_url(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='master']/m:file/m:FLocat")
    for fl in flocats:
        assert fl.get("LOCTYPE") == "URL"


def test_fileSec_alto_path_contains_corpus_slug(beatus_pages, beatus_meta):
    """Le chemin ALTO référence le bon corpus_slug."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file/m:FLocat")
    for fl in flocats:
        href = fl.get(f"{{{_XLINK_NS}}}href", "")
        assert "beatus-lat8878" in href


def test_fileSec_alto_path_contains_folio_label(beatus_pages, beatus_meta):
    """Le chemin ALTO référence le bon folio_label."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file/m:FLocat")
    hrefs = [fl.get(f"{{{_XLINK_NS}}}href", "") for fl in flocats]
    assert any("f233-hr" in h for h in hrefs)
    assert any("f233-br" in h for h in hrefs)


def test_fileSec_alto_path_ends_with_alto_xml(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file/m:FLocat")
    for fl in flocats:
        href = fl.get(f"{{{_XLINK_NS}}}href", "")
        assert href.endswith("alto.xml"), f"ALTO href ne finit pas par alto.xml : {href}"


def test_fileSec_alto_mimetype(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    files = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file")
    for f in files:
        assert f.get("MIMETYPE") == "text/xml"


def test_fileSec_file_ids_are_unique(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    all_files = _xp(root, "m:fileSec//m:file")
    ids = [f.get("ID") for f in all_files]
    assert len(ids) == len(set(ids)), f"IDs de fichiers en double : {ids}"


# ---------------------------------------------------------------------------
# Tests — structMap PHYSICAL (séquence)
# ---------------------------------------------------------------------------

def test_structMap_physical_div_count(beatus_pages, beatus_meta):
    """2 pages → 2 div TYPE=page dans la structMap physique."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    assert len(divs) == 2


def test_structMap_physical_order_respects_sequence():
    """Les pages sont triées par sequence même si la liste est dans le désordre."""
    pages = [
        _make_page("ms-f003r", "f003r", sequence=3),
        _make_page("ms-f001r", "f001r", sequence=1),
        _make_page("ms-f002r", "f002r", sequence=2),
    ]
    meta = {"manuscript_id": "ms-001", "label": "Test", "corpus_slug": "test"}
    root = _parse(generate_mets(pages, meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    orders = [int(d.get("ORDER")) for d in divs]
    assert orders == [1, 2, 3]


def test_structMap_physical_order_values(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    orders = sorted(int(d.get("ORDER")) for d in divs)
    assert orders == [233, 234]


def test_structMap_physical_orderlabel(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    labels = {d.get("ORDERLABEL") for d in divs}
    assert "f233-hr" in labels
    assert "f233-br" in labels


def test_structMap_physical_each_page_has_3_fptr(beatus_pages, beatus_meta):
    """Chaque div page a exactement 3 fptr (master + deriv + alto)."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    for div in divs:
        fptrs = div.findall(f"{{{_METS_NS}}}fptr")
        assert len(fptrs) == 3, (
            f"Div {div.get('ORDERLABEL')} a {len(fptrs)} fptr, attendu 3"
        )


def test_structMap_physical_fptr_fileids_exist_in_fileSec(beatus_pages, beatus_meta):
    """Les FILEID des fptr existent bien dans la fileSec."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    file_ids = {f.get("ID") for f in _xp(root, "m:fileSec//m:file")}
    fptr_ids = {f.get("FILEID") for f in _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:fptr")}
    assert fptr_ids.issubset(file_ids), f"FILEID manquants : {fptr_ids - file_ids}"


def test_structMap_physical_fptr_references_correct_files():
    """Les FILEID référencent les fichiers correspondant à la bonne page."""
    page = _make_page("my-ms-0042v", "0042v", sequence=42)
    meta = {"manuscript_id": "ms-x", "label": "X", "corpus_slug": "corpus-x"}
    root = _parse(generate_mets([page], meta))

    div = _one(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    fptr_ids = {f.get("FILEID") for f in div.findall(f"{{{_METS_NS}}}fptr")}

    # Les IDs doivent contenir la version safe du page_id
    safe = "my_ms_0042v"
    assert f"IMG_MASTER_{safe}" in fptr_ids
    assert f"IMG_DERIV_{safe}"  in fptr_ids
    assert f"ALTO_{safe}"       in fptr_ids


# ---------------------------------------------------------------------------
# Tests — structMap LOGICAL
# ---------------------------------------------------------------------------

def test_structMap_logical_has_one_manuscript_div(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    divs = _xp(root, "m:structMap[@TYPE='LOGICAL']/m:div[@TYPE='manuscript']")
    assert len(divs) == 1


def test_structMap_logical_div_label(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    div = _one(root, "m:structMap[@TYPE='LOGICAL']/m:div[@TYPE='manuscript']")
    assert div.get("LABEL") == "Beatus de Saint-Sever"


def test_structMap_logical_div_dmdid(beatus_pages, beatus_meta):
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    div = _one(root, "m:structMap[@TYPE='LOGICAL']/m:div[@TYPE='manuscript']")
    assert div.get("DMDID") == "DMD_1"


def test_structMap_logical_no_page_divs(beatus_pages, beatus_meta):
    """MVP : aucun sous-div de page dans la structMap logique."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))
    page_divs = _xp(root, "m:structMap[@TYPE='LOGICAL']//m:div[@TYPE='page']")
    assert len(page_divs) == 0


# ---------------------------------------------------------------------------
# Tests — erreurs explicites
# ---------------------------------------------------------------------------

def test_empty_masters_raises_value_error():
    meta = {"manuscript_id": "ms-x", "label": "X", "corpus_slug": "x"}
    with pytest.raises(ValueError, match="vide"):
        generate_mets([], meta)


def test_missing_manuscript_id_raises():
    pages = [_make_page("ms-0001r", "0001r", 1)]
    with pytest.raises(ValueError, match="manuscript_id"):
        generate_mets(pages, {"label": "X", "corpus_slug": "x"})


def test_missing_label_raises():
    pages = [_make_page("ms-0001r", "0001r", 1)]
    with pytest.raises(ValueError, match="label"):
        generate_mets(pages, {"manuscript_id": "ms-x", "corpus_slug": "x"})


def test_missing_corpus_slug_raises():
    pages = [_make_page("ms-0001r", "0001r", 1)]
    with pytest.raises(ValueError, match="corpus_slug"):
        generate_mets(pages, {"manuscript_id": "ms-x", "label": "X"})


def test_empty_string_corpus_slug_raises():
    pages = [_make_page("ms-0001r", "0001r", 1)]
    with pytest.raises(ValueError, match="corpus_slug"):
        generate_mets(pages, {"manuscript_id": "ms-x", "label": "X", "corpus_slug": ""})


# ---------------------------------------------------------------------------
# Tests — write_mets
# ---------------------------------------------------------------------------

def test_write_mets_creates_file(tmp_path, beatus_pages, beatus_meta):
    xml_str = generate_mets(beatus_pages, beatus_meta)
    write_mets(xml_str, "beatus-lat8878", base_data_dir=tmp_path)
    expected = tmp_path / "corpora" / "beatus-lat8878" / "mets.xml"
    assert expected.exists()


def test_write_mets_creates_parent_dirs(tmp_path, beatus_pages, beatus_meta):
    xml_str = generate_mets(beatus_pages, beatus_meta)
    write_mets(xml_str, "beatus-lat8878", base_data_dir=tmp_path)
    assert (tmp_path / "corpora" / "beatus-lat8878").is_dir()


def test_write_mets_content_is_valid_xml(tmp_path, beatus_pages, beatus_meta):
    xml_str = generate_mets(beatus_pages, beatus_meta)
    write_mets(xml_str, "beatus-lat8878", base_data_dir=tmp_path)
    path = tmp_path / "corpora" / "beatus-lat8878" / "mets.xml"
    root = etree.parse(str(path)).getroot()
    assert root.tag == f"{{{_METS_NS}}}mets"


# ---------------------------------------------------------------------------
# Tests — scénarios réalistes Sprint 2
# ---------------------------------------------------------------------------

def test_beatus_full_mets(beatus_pages, beatus_meta):
    """Scénario complet Beatus HR + BR : 2 pages, métadonnées complètes."""
    root = _parse(generate_mets(beatus_pages, beatus_meta))

    # Identité
    assert root.get("OBJID") == "BnF-Latin-8878"

    # 2 pages dans fileSec
    assert len(_xp(root, "m:fileSec/m:fileGrp[@USE='master']/m:file")) == 2

    # Séquence physique
    orders = sorted(
        int(d.get("ORDER"))
        for d in _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    )
    assert orders == [233, 234]

    # URLs Gallica présentes
    hrefs = [
        el.get(f"{{{_XLINK_NS}}}href", "")
        for el in _xp(root, "m:fileSec/m:fileGrp[@USE='master']/m:file/m:FLocat")
    ]
    assert any("btv1b52505441p" in h for h in hrefs)

    # shelfmark dans DC
    assert len(_xp(root, "m:dmdSec//dc:relation")) == 1


def test_grandes_chroniques_mets(chroniques_pages, chroniques_meta):
    """Scénario Grandes Chroniques : 1 page, langue fr."""
    root = _parse(generate_mets(chroniques_pages, chroniques_meta))

    assert root.get("OBJID") == "BnF-btv1b84472995"
    lang = _one(root, "m:dmdSec//dc:language")
    assert lang.text == "fr"

    # 1 fichier par fileGrp
    for use in ("master", "derivative_web", "alto"):
        files = _xp(root, f"m:fileSec/m:fileGrp[@USE='{use}']/m:file")
        assert len(files) == 1, f"fileGrp[@USE='{use}'] : attendu 1, obtenu {len(files)}"

    # ALTO path contient grandes-chroniques + f16
    flocats = _xp(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file/m:FLocat")
    href = flocats[0].get(f"{{{_XLINK_NS}}}href", "")
    assert "grandes-chroniques" in href
    assert "f16" in href


def test_single_page_manuscript():
    """Un manuscrit à 1 seule page est valide."""
    pages = [_make_page("ms-0001r", "0001r", 1)]
    meta = {"manuscript_id": "ms-solo", "label": "Solo MS", "corpus_slug": "solo"}
    root = _parse(generate_mets(pages, meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    assert len(divs) == 1


def test_many_pages_sequence_order():
    """10 pages dans le désordre → structMap PHYSICAL dans l'ordre croissant."""
    import random
    pages = [_make_page(f"ms-f{i:03d}r", f"f{i:03d}r", i) for i in range(1, 11)]
    random.shuffle(pages)
    meta = {"manuscript_id": "ms-big", "label": "Big MS", "corpus_slug": "big-ms"}
    root = _parse(generate_mets(pages, meta))
    divs = _xp(root, "m:structMap[@TYPE='PHYSICAL']//m:div[@TYPE='page']")
    orders = [int(d.get("ORDER")) for d in divs]
    assert orders == list(range(1, 11))


def test_alto_path_uses_base_data_dir(tmp_path):
    """Le chemin ALTO dans fileSec utilise bien le base_data_dir passé."""
    pages = [_make_page("ms-0001r", "0001r", 1)]
    meta = {"manuscript_id": "ms-x", "label": "X", "corpus_slug": "corp-x"}
    root = _parse(generate_mets(pages, meta, base_data_dir=tmp_path))
    fl = _one(root, "m:fileSec/m:fileGrp[@USE='alto']/m:file/m:FLocat")
    href = fl.get(f"{{{_XLINK_NS}}}href", "")
    assert str(tmp_path) in href
