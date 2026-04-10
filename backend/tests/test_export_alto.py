"""
Tests du générateur ALTO v4 (Sprint 3 — Session A).

Vérifie :
- XML produit est valide (parseable par lxml)
- Correspondance exacte bbox → HPOS/VPOS/WIDTH/HEIGHT
- text_block / margin / rubric → TextBlock
- miniature / decorated_initial → Illustration
- other → ComposedBlock
- Texte OCR présent dans TextBlock quand disponible
- Fallback diplomatic_text dans le premier TextBlock si aucun bloc OCR par région
- Master sans régions → ALTO valide avec PrintSpace vide
- Région invalide → ValueError explicite (jamais ALTO partiel)
- Dimensions de page (WIDTH/HEIGHT) issues de master.image
- OCRProcessing présent si master.processing, absent sinon
- Attribut TYPE sur Illustration (valeur du RegionType)
- Page ID contient le page_id du master
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
from app.services.export.alto import generate_alto, write_alto

# ── Namespace ALTO v4 ─────────────────────────────────────────────────────
_ALTO_NS = "http://www.loc.gov/standards/alto/ns-v4#"
_A = f"{{{_ALTO_NS}}}"


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_master(
    page_id: str = "test-ms-0001r",
    sequence: int = 1,
    regions: list | None = None,
    ocr: OCRResult | None = None,
    width: int = 1500,
    height: int = 2000,
    with_processing: bool = False,
) -> PageMaster:
    if regions is None:
        regions = []
    processing = None
    if with_processing:
        processing = ProcessingInfo(
            provider="google_ai_studio",
            model_id="gemini-2.0-flash",
            model_display_name="Gemini 2.0 Flash",
            prompt_version="prompts/medieval-illuminated/primary_v1.txt",
            raw_response_path="/data/gemini_raw.json",
            processed_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
    return PageMaster(
        page_id=page_id,
        corpus_profile="medieval-illuminated",
        manuscript_id="ms-test",
        folio_label="0001r",
        sequence=sequence,
        image={
            "master": "https://example.com/img.jpg",
            "derivative_web": "/data/deriv.jpg",
            "thumbnail": "/data/thumb.jpg",
            "width": width,
            "height": height,
        },
        layout={"regions": regions},
        ocr=ocr,
        processing=processing,
        editorial=EditorialInfo(status=EditorialStatus.MACHINE_DRAFT),
    )


def _parse(xml_str: str) -> etree._Element:
    """Parse une chaîne XML et retourne la racine."""
    return etree.fromstring(xml_str.encode("utf-8"))


def _xpath(root: etree._Element, path: str) -> list:
    return root.xpath(path, namespaces={"a": _ALTO_NS})


def _one(root: etree._Element, path: str) -> etree._Element:
    results = _xpath(root, path)
    assert len(results) == 1, f"Expected 1 match for {path!r}, got {len(results)}"
    return results[0]


# ---------------------------------------------------------------------------
# Synthetic master.json fixtures (équivalents aux 3 master.json du Sprint 2)
# ---------------------------------------------------------------------------

@pytest.fixture
def master_text_only():
    """Master simulant une page texte (seul TextBlock, OCR global)."""
    return _make_master(
        page_id="beatus-hr-0001r",
        sequence=1,
        regions=[
            {"id": "r1", "type": "text_block", "bbox": [50, 100, 1400, 1800], "confidence": 0.92},
        ],
        ocr=OCRResult(
            diplomatic_text="Incipit explanatio beati Ieronimi",
            language="la",
            confidence=0.92,
        ),
        width=1500,
        height=2000,
        with_processing=True,
    )


@pytest.fixture
def master_mixed_regions():
    """Master simulant un folio enluminé (texte + miniature + initial décoré)."""
    return _make_master(
        page_id="beatus-br-0013r",
        sequence=13,
        regions=[
            {"id": "r1", "type": "miniature", "bbox": [0, 0, 1500, 800], "confidence": 0.95},
            {"id": "r2", "type": "decorated_initial", "bbox": [50, 820, 200, 200], "confidence": 0.88},
            {"id": "r3", "type": "text_block", "bbox": [260, 820, 1200, 200], "confidence": 0.90},
            {"id": "r4", "type": "rubric", "bbox": [50, 1040, 1400, 80], "confidence": 0.85},
            {"id": "r5", "type": "margin", "bbox": [0, 100, 45, 1800], "confidence": 0.70},
        ],
        ocr=OCRResult(
            diplomatic_text="Sequitur de bestia",
            language="la",
            confidence=0.90,
        ),
        width=1500,
        height=2000,
    )


@pytest.fixture
def master_with_per_region_ocr():
    """Master avec OCR indexé par region_id dans ocr.blocks."""
    return _make_master(
        page_id="chroniques-f016",
        sequence=16,
        regions=[
            {"id": "r1", "type": "text_block", "bbox": [100, 100, 600, 400], "confidence": 0.91},
            {"id": "r2", "type": "text_block", "bbox": [100, 520, 600, 300], "confidence": 0.87},
            {"id": "r3", "type": "miniature", "bbox": [720, 100, 700, 800], "confidence": 0.96},
        ],
        ocr=OCRResult(
            diplomatic_text="[global fallback]",
            blocks=[
                {"region_id": "r1", "text": "Cy commence le prologue", "confidence": 0.91},
                {"region_id": "r2", "text": "Des grandes chroniques de France", "confidence": 0.87},
            ],
            language="fr",
            confidence=0.89,
        ),
        width=1500,
        height=2000,
    )


# ---------------------------------------------------------------------------
# Tests — validité XML
# ---------------------------------------------------------------------------

def test_generate_alto_returns_string(master_text_only):
    result = generate_alto(master_text_only)
    assert isinstance(result, str)


def test_generate_alto_valid_xml(master_text_only):
    """Le XML produit doit être parseable par lxml sans erreur."""
    xml_str = generate_alto(master_text_only)
    root = _parse(xml_str)
    assert root is not None


def test_generate_alto_valid_xml_mixed(master_mixed_regions):
    xml_str = generate_alto(master_mixed_regions)
    root = _parse(xml_str)
    assert root is not None


def test_generate_alto_valid_xml_per_region_ocr(master_with_per_region_ocr):
    xml_str = generate_alto(master_with_per_region_ocr)
    root = _parse(xml_str)
    assert root is not None


def test_generate_alto_xml_declaration(master_text_only):
    """Le XML doit commencer par la déclaration XML."""
    xml_str = generate_alto(master_text_only)
    assert xml_str.startswith("<?xml")


def test_generate_alto_alto_namespace(master_text_only):
    """L'élément racine doit utiliser le namespace ALTO v4."""
    root = _parse(generate_alto(master_text_only))
    assert root.tag == f"{{{_ALTO_NS}}}alto"


def test_generate_alto_empty_regions():
    """Un master sans régions produit un ALTO valide avec PrintSpace vide."""
    master = _make_master(regions=[])
    xml_str = generate_alto(master)
    root = _parse(xml_str)
    ps = _one(root, "//a:PrintSpace")
    assert len(list(ps)) == 0  # aucun enfant


# ---------------------------------------------------------------------------
# Tests — bbox HPOS/VPOS/WIDTH/HEIGHT (R03 correspondance directe)
# ---------------------------------------------------------------------------

def test_text_block_bbox_exact(master_text_only):
    """HPOS/VPOS/WIDTH/HEIGHT du TextBlock correspondent exactement à bbox [x,y,w,h]."""
    root = _parse(generate_alto(master_text_only))
    tb = _one(root, "//a:TextBlock[@ID='r1']")
    assert tb.get("HPOS") == "50"
    assert tb.get("VPOS") == "100"
    assert tb.get("WIDTH") == "1400"
    assert tb.get("HEIGHT") == "1800"


def test_illustration_bbox_exact(master_mixed_regions):
    """HPOS/VPOS/WIDTH/HEIGHT de l'Illustration correspondent exactement à bbox."""
    root = _parse(generate_alto(master_mixed_regions))
    ill = _one(root, "//a:Illustration[@ID='r1']")
    assert ill.get("HPOS") == "0"
    assert ill.get("VPOS") == "0"
    assert ill.get("WIDTH") == "1500"
    assert ill.get("HEIGHT") == "800"


def test_decorated_initial_bbox_exact(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    ill = _one(root, "//a:Illustration[@ID='r2']")
    assert ill.get("HPOS") == "50"
    assert ill.get("VPOS") == "820"
    assert ill.get("WIDTH") == "200"
    assert ill.get("HEIGHT") == "200"


def test_multiple_text_blocks_bbox(master_with_per_region_ocr):
    root = _parse(generate_alto(master_with_per_region_ocr))
    tb1 = _one(root, "//a:TextBlock[@ID='r1']")
    tb2 = _one(root, "//a:TextBlock[@ID='r2']")

    assert (tb1.get("HPOS"), tb1.get("VPOS"), tb1.get("WIDTH"), tb1.get("HEIGHT")) == (
        "100", "100", "600", "400"
    )
    assert (tb2.get("HPOS"), tb2.get("VPOS"), tb2.get("WIDTH"), tb2.get("HEIGHT")) == (
        "100", "520", "600", "300"
    )


# ---------------------------------------------------------------------------
# Tests — mapping RegionType → élément ALTO
# ---------------------------------------------------------------------------

def test_text_block_produces_TextBlock(master_text_only):
    root = _parse(generate_alto(master_text_only))
    assert len(_xpath(root, "//a:TextBlock")) == 1
    assert len(_xpath(root, "//a:Illustration")) == 0


def test_miniature_produces_Illustration(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    ill = _one(root, "//a:Illustration[@ID='r1']")
    assert ill.get("TYPE") == "miniature"


def test_decorated_initial_produces_Illustration(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    ill = _one(root, "//a:Illustration[@ID='r2']")
    assert ill.get("TYPE") == "decorated_initial"


def test_rubric_produces_TextBlock(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    # r4 est rubric → doit être un TextBlock, pas une Illustration
    tb = _one(root, "//a:TextBlock[@ID='r4']")
    assert tb is not None
    illustrations = _xpath(root, "//a:Illustration[@ID='r4']")
    assert len(illustrations) == 0


def test_margin_produces_TextBlock(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    tb = _one(root, "//a:TextBlock[@ID='r5']")
    assert tb is not None


def test_other_region_produces_ComposedBlock():
    master = _make_master(
        regions=[{"id": "r1", "type": "other", "bbox": [10, 10, 100, 100], "confidence": 0.5}]
    )
    root = _parse(generate_alto(master))
    cb = _one(root, "//a:ComposedBlock[@ID='r1']")
    assert cb.get("HPOS") == "10"
    assert cb.get("VPOS") == "10"
    assert cb.get("WIDTH") == "100"
    assert cb.get("HEIGHT") == "100"
    assert len(_xpath(root, "//a:TextBlock")) == 0
    assert len(_xpath(root, "//a:Illustration")) == 0


def test_mixed_regions_counts(master_mixed_regions):
    """Folio enluminé : 3 TextBlock (text_block + rubric + margin) + 2 Illustration."""
    root = _parse(generate_alto(master_mixed_regions))
    assert len(_xpath(root, "//a:TextBlock")) == 3
    assert len(_xpath(root, "//a:Illustration")) == 2


# ---------------------------------------------------------------------------
# Tests — contenu OCR dans les TextBlocks
# ---------------------------------------------------------------------------

def test_diplomatic_text_in_first_text_block(master_text_only):
    """Le diplomatic_text global va dans le premier TextBlock si pas de per-region OCR."""
    root = _parse(generate_alto(master_text_only))
    strings = _xpath(root, "//a:TextBlock[@ID='r1']/a:TextLine/a:String")
    assert len(strings) == 1
    assert strings[0].get("CONTENT") == "Incipit explanatio beati Ieronimi"


def test_per_region_ocr_blocks_used(master_with_per_region_ocr):
    """Quand ocr.blocks contient des region_id, chaque TextBlock a son propre texte."""
    root = _parse(generate_alto(master_with_per_region_ocr))

    s1 = _one(root, "//a:TextBlock[@ID='r1']/a:TextLine/a:String")
    s2 = _one(root, "//a:TextBlock[@ID='r2']/a:TextLine/a:String")

    assert s1.get("CONTENT") == "Cy commence le prologue"
    assert s2.get("CONTENT") == "Des grandes chroniques de France"


def test_per_region_ocr_no_fallback_in_second_block(master_with_per_region_ocr):
    """Le fallback global N'est PAS répété dans d'autres blocs quand per-region OCR existe."""
    root = _parse(generate_alto(master_with_per_region_ocr))
    strings = _xpath(root, "//a:String[@CONTENT='[global fallback]']")
    assert len(strings) == 0


def test_no_ocr_text_block_is_empty():
    """TextBlock sans OCR disponible reste vide (valide ALTO)."""
    master = _make_master(
        regions=[{"id": "r1", "type": "text_block", "bbox": [0, 0, 100, 100], "confidence": 0.8}],
        ocr=None,
    )
    root = _parse(generate_alto(master))
    tb = _one(root, "//a:TextBlock[@ID='r1']")
    assert len(list(tb)) == 0  # pas d'enfants TextLine


def test_text_content_not_in_illustration():
    """Les Illustrations ne doivent pas contenir de TextLine."""
    master = _make_master(
        regions=[{"id": "r1", "type": "miniature", "bbox": [0, 0, 500, 500], "confidence": 0.9}],
        ocr=OCRResult(diplomatic_text="Some text that shouldn't be in illustration"),
    )
    root = _parse(generate_alto(master))
    assert len(_xpath(root, "//a:Illustration/a:TextLine")) == 0
    assert len(_xpath(root, "//a:Illustration/a:String")) == 0


def test_string_wc_attribute_present(master_text_only):
    """L'attribut WC (word confidence) est présent sur les éléments String."""
    root = _parse(generate_alto(master_text_only))
    strings = _xpath(root, "//a:String")
    for s in strings:
        assert s.get("WC") is not None
        wc = float(s.get("WC"))
        assert 0.0 <= wc <= 1.0


def test_string_bbox_matches_region_bbox(master_text_only):
    """Le String hérite des coordonnées bbox de sa région."""
    root = _parse(generate_alto(master_text_only))
    s = _one(root, "//a:TextBlock[@ID='r1']/a:TextLine/a:String")
    assert s.get("HPOS") == "50"
    assert s.get("VPOS") == "100"
    assert s.get("WIDTH") == "1400"
    assert s.get("HEIGHT") == "1800"


# ---------------------------------------------------------------------------
# Tests — dimensions de page
# ---------------------------------------------------------------------------

def test_page_width_height_from_image(master_text_only):
    root = _parse(generate_alto(master_text_only))
    page = _one(root, "//a:Page")
    assert page.get("WIDTH") == "1500"
    assert page.get("HEIGHT") == "2000"


def test_print_space_dimensions_match_page(master_text_only):
    root = _parse(generate_alto(master_text_only))
    ps = _one(root, "//a:PrintSpace")
    assert ps.get("HPOS") == "0"
    assert ps.get("VPOS") == "0"
    assert ps.get("WIDTH") == "1500"
    assert ps.get("HEIGHT") == "2000"


def test_page_physical_img_nr_is_sequence(master_mixed_regions):
    root = _parse(generate_alto(master_mixed_regions))
    page = _one(root, "//a:Page")
    assert page.get("PHYSICAL_IMG_NR") == "13"


def test_page_id_contains_page_id(master_text_only):
    root = _parse(generate_alto(master_text_only))
    page = _one(root, "//a:Page")
    assert "beatus-hr-0001r" in page.get("ID", "")


# ---------------------------------------------------------------------------
# Tests — OCRProcessing (metadata de traitement)
# ---------------------------------------------------------------------------

def test_ocr_processing_present_when_processing_info(master_text_only):
    """OCRProcessing est présent si master.processing est défini."""
    root = _parse(generate_alto(master_text_only))
    ocr_proc = _one(root, "//a:OCRProcessing")
    assert ocr_proc is not None


def test_ocr_processing_model_name(master_text_only):
    root = _parse(generate_alto(master_text_only))
    name = _one(root, "//a:processingSoftware/a:softwareName")
    assert name.text == "Gemini 2.0 Flash"


def test_ocr_processing_prompt_version(master_text_only):
    root = _parse(generate_alto(master_text_only))
    version = _one(root, "//a:processingSoftware/a:softwareVersion")
    assert "primary_v1.txt" in version.text


def test_ocr_processing_datetime(master_text_only):
    root = _parse(generate_alto(master_text_only))
    dt = _one(root, "//a:processingDateTime")
    assert "2024-06-15" in dt.text


def test_ocr_processing_absent_without_processing_info():
    """OCRProcessing est absent si master.processing est None."""
    master = _make_master(with_processing=False)
    root = _parse(generate_alto(master))
    assert len(_xpath(root, "//a:OCRProcessing")) == 0


def test_software_creator_is_scriptorium_ai(master_text_only):
    root = _parse(generate_alto(master_text_only))
    creator = _one(root, "//a:processingSoftware/a:softwareCreator")
    assert creator.text == "Scriptorium AI"


# ---------------------------------------------------------------------------
# Tests — source image
# ---------------------------------------------------------------------------

def test_source_filename_from_original_url(master_text_only):
    root = _parse(generate_alto(master_text_only))
    fn = _one(root, "//a:fileName")
    assert fn.text == "https://example.com/img.jpg"


# ---------------------------------------------------------------------------
# Tests — erreur explicite sur region invalide
# ---------------------------------------------------------------------------

def test_invalid_region_raises_value_error():
    """Une région avec bbox invalide dans le layout lève ValueError (jamais ALTO partiel)."""
    master = _make_master(
        regions=[
            {"id": "r1", "type": "text_block", "bbox": [0, 0, 0, 100], "confidence": 0.9},
        ]
    )
    with pytest.raises(ValueError, match="Région"):
        generate_alto(master)


def test_invalid_region_negative_bbox_raises():
    master = _make_master(
        regions=[
            {"id": "r1", "type": "text_block", "bbox": [-5, 0, 100, 100], "confidence": 0.9},
        ]
    )
    with pytest.raises(ValueError, match="Région"):
        generate_alto(master)


def test_invalid_region_missing_field_raises():
    """Une région sans champ 'type' lève ValueError."""
    master = _make_master(
        regions=[
            {"id": "r1", "bbox": [0, 0, 100, 100], "confidence": 0.9},  # manque 'type'
        ]
    )
    with pytest.raises(ValueError, match="Région"):
        generate_alto(master)


def test_valid_region_after_nothing_invalid_no_partial_output():
    """Si la première région est invalide, aucun ALTO n'est produit (pas de sortie partielle)."""
    master = _make_master(
        regions=[
            {"id": "r_bad", "type": "text_block", "bbox": [0, 0, -1, 100], "confidence": 0.9},
            {"id": "r_good", "type": "miniature", "bbox": [0, 0, 100, 100], "confidence": 0.9},
        ]
    )
    with pytest.raises(ValueError):
        generate_alto(master)


# ---------------------------------------------------------------------------
# Tests — write_alto
# ---------------------------------------------------------------------------

def test_write_alto_creates_file(tmp_path):
    master = _make_master()
    xml_str = generate_alto(master)
    out = tmp_path / "alto.xml"
    write_alto(xml_str, out)
    assert out.exists()


def test_write_alto_creates_parent_dirs(tmp_path):
    master = _make_master()
    xml_str = generate_alto(master)
    out = tmp_path / "data" / "corpora" / "test" / "pages" / "0001r" / "alto.xml"
    write_alto(xml_str, out)
    assert out.exists()


def test_write_alto_content_is_valid_xml(tmp_path):
    master = _make_master(
        regions=[{"id": "r1", "type": "text_block", "bbox": [0, 0, 100, 100], "confidence": 0.8}]
    )
    xml_str = generate_alto(master)
    out = tmp_path / "alto.xml"
    write_alto(xml_str, out)
    root = etree.parse(str(out)).getroot()
    assert root.tag == f"{{{_ALTO_NS}}}alto"


# ---------------------------------------------------------------------------
# Tests — scénarios réalistes Sprint 2 (3 "master.json" simulés)
# ---------------------------------------------------------------------------

def test_beatus_hr_folio_alto():
    """Simule le folio Beatus HR : page texte dense avec OCR global."""
    master = _make_master(
        page_id="beatus-lat8878-hr-f233",
        sequence=233,
        regions=[
            {"id": "r1", "type": "text_block", "bbox": [42, 58, 1410, 1880], "confidence": 0.93},
            {"id": "r2", "type": "rubric", "bbox": [42, 58, 400, 40], "confidence": 0.88},
            {"id": "r3", "type": "margin", "bbox": [1460, 58, 40, 1880], "confidence": 0.60},
        ],
        ocr=OCRResult(
            diplomatic_text="Et post hec uidit angelum descendentem de celo",
            language="la",
            confidence=0.93,
        ),
        width=1500,
        height=2000,
        with_processing=True,
    )
    root = _parse(generate_alto(master))
    assert len(_xpath(root, "//a:TextBlock")) == 3
    assert len(_xpath(root, "//a:Illustration")) == 0
    # OCR dans le premier TextBlock
    strings = _xpath(root, "//a:String")
    assert any("angelum" in (s.get("CONTENT") or "") for s in strings)


def test_beatus_br_folio_alto():
    """Simule le folio Beatus BR : miniature + texte."""
    master = _make_master(
        page_id="beatus-lat8878-br-f233",
        sequence=233,
        regions=[
            {"id": "r1", "type": "miniature", "bbox": [0, 0, 1500, 900], "confidence": 0.97},
            {"id": "r2", "type": "decorated_initial", "bbox": [42, 920, 120, 120], "confidence": 0.85},
            {"id": "r3", "type": "text_block", "bbox": [180, 920, 1280, 120], "confidence": 0.91},
        ],
        ocr=OCRResult(
            diplomatic_text="Incipit liber beati",
            language="la",
            confidence=0.91,
        ),
        width=1500,
        height=2000,
    )
    root = _parse(generate_alto(master))
    # Miniature + initial → Illustration
    assert len(_xpath(root, "//a:Illustration")) == 2
    # Un TextBlock
    assert len(_xpath(root, "//a:TextBlock")) == 1
    # Les Illustrations ne sont pas des TextBlocks
    ill_ids = {el.get("ID") for el in _xpath(root, "//a:Illustration")}
    tb_ids = {el.get("ID") for el in _xpath(root, "//a:TextBlock")}
    assert ill_ids.isdisjoint(tb_ids)


def test_grandes_chroniques_folio_alto():
    """Simule le folio Grandes Chroniques : texte en français, OCR par région."""
    master = _make_master(
        page_id="chroniques-btv1b84472995-f16",
        sequence=16,
        regions=[
            {"id": "r1", "type": "miniature", "bbox": [20, 20, 700, 600], "confidence": 0.96},
            {"id": "r2", "type": "text_block", "bbox": [740, 20, 720, 600], "confidence": 0.89},
            {"id": "r3", "type": "text_block", "bbox": [20, 640, 1440, 1300], "confidence": 0.91},
        ],
        ocr=OCRResult(
            diplomatic_text="",
            blocks=[
                {"region_id": "r2", "text": "Ci commence le prolog", "confidence": 0.89},
                {"region_id": "r3", "text": "Des roys de france", "confidence": 0.91},
            ],
            language="fr",
            confidence=0.90,
        ),
        width=1460,
        height=1960,
    )
    root = _parse(generate_alto(master))
    assert len(_xpath(root, "//a:Illustration")) == 1
    assert len(_xpath(root, "//a:TextBlock")) == 2

    s2 = _one(root, "//a:TextBlock[@ID='r2']/a:TextLine/a:String")
    s3 = _one(root, "//a:TextBlock[@ID='r3']/a:TextLine/a:String")
    assert s2.get("CONTENT") == "Ci commence le prolog"
    assert s3.get("CONTENT") == "Des roys de france"

    # Dimensions de page correctes
    page = _one(root, "//a:Page")
    assert page.get("WIDTH") == "1460"
    assert page.get("HEIGHT") == "1960"
