"""
Tests de l'endpoint GET /api/v1/search (Sprint 4 — recherche indexée).

Stratégie :
  - Données indexées directement dans la table page_search (BDD en mémoire)
  - Vérifie : 422 (paramètre manquant / trop court), résultats vides,
    correspondance OCR, insensibilité casse et accents, tri par score,
    extrait (excerpt) présent.
"""
# 1. stdlib
import uuid

# 2. third-party
import pytest

# 3. local
from app.models.page_search import PageSearchIndex
from tests.conftest_api import async_client, db_session  # noqa: F401


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _index_page(
    db,
    page_id: str | None = None,
    diplomatic_text: str = "",
    translation_fr: str = "",
    tags: str = "",
    corpus_profile: str = "medieval-illuminated",
    manuscript_id: str = "ms-test",
    folio_label: str = "f001r",
) -> str:
    """Insère une entrée dans page_search et retourne le page_id."""
    pid = page_id or str(uuid.uuid4())
    entry = PageSearchIndex(
        page_id=pid,
        corpus_profile=corpus_profile,
        manuscript_id=manuscript_id,
        folio_label=folio_label,
        diplomatic_text=diplomatic_text,
        translation_fr=translation_fr,
        tags=tags,
    )
    db.add(entry)
    await db.commit()
    return pid


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_missing_q(async_client):
    """q est obligatoire — 422 si absent."""
    resp = await async_client.get("/api/v1/search")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_q_too_short(async_client):
    """q doit faire au moins 2 caractères — 422 si trop court."""
    resp = await async_client.get("/api/v1/search?q=a")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_results(async_client):
    """Retourne [] quand aucune page ne correspond."""
    resp = await async_client.get("/api/v1/search?q=rien")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_returns_list(async_client):
    """Le type de retour est toujours une liste."""
    resp = await async_client.get("/api/v1/search?q=texte")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_finds_ocr_text(async_client, db_session):
    """Trouve une page dont diplomatic_text contient la requête."""
    page_id = await _index_page(db_session, diplomatic_text="Incipit liber primus")

    resp = await async_client.get("/api/v1/search?q=Incipit")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["page_id"] == page_id


@pytest.mark.asyncio
async def test_search_case_insensitive(async_client, db_session):
    """La recherche est insensible à la casse."""
    page_id = await _index_page(db_session, diplomatic_text="INCIPIT LIBER")

    resp = await async_client.get("/api/v1/search?q=incipit")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any(r["page_id"] == page_id for r in results)


@pytest.mark.asyncio
async def test_search_accent_insensitive(async_client, db_session):
    """La recherche est insensible aux accents."""
    page_id = await _index_page(
        db_session, diplomatic_text="Édition française médiévale"
    )

    resp = await async_client.get("/api/v1/search?q=edition")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any(r["page_id"] == page_id for r in results)


@pytest.mark.asyncio
async def test_search_finds_translation_fr(async_client, db_session):
    """Trouve également dans translation_fr."""
    page_id = await _index_page(
        db_session, translation_fr="Ici commence le premier livre"
    )

    resp = await async_client.get("/api/v1/search?q=premier")
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["page_id"] == page_id for r in results)


@pytest.mark.asyncio
async def test_search_no_match_returns_empty(async_client, db_session):
    """Ne retourne rien quand la requête ne correspond à aucun texte."""
    await _index_page(db_session, diplomatic_text="Incipit liber")

    resp = await async_client.get("/api/v1/search?q=xyznomatch")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_result_has_excerpt(async_client, db_session):
    """Chaque résultat contient un champ excerpt non vide."""
    await _index_page(db_session, diplomatic_text="Incipit liber primus")

    resp = await async_client.get("/api/v1/search?q=liber")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert results[0]["excerpt"] != ""


@pytest.mark.asyncio
async def test_search_sorted_by_score_desc(async_client, db_session):
    """Les résultats sont triés par score décroissant."""
    page_id_1 = await _index_page(
        db_session, diplomatic_text="liber liber liber"
    )
    page_id_2 = await _index_page(
        db_session, diplomatic_text="liber unus"
    )

    resp = await async_client.get("/api/v1/search?q=liber")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert results[0]["page_id"] == page_id_1


@pytest.mark.asyncio
async def test_search_result_fields(async_client, db_session):
    """Chaque résultat expose les champs attendus."""
    await _index_page(db_session, diplomatic_text="Incipit liber")

    resp = await async_client.get("/api/v1/search?q=Incipit")
    assert resp.status_code == 200
    result = resp.json()[0]
    assert "page_id" in result
    assert "folio_label" in result
    assert "manuscript_id" in result
    assert "excerpt" in result
    assert "score" in result
    assert "corpus_profile" in result


@pytest.mark.asyncio
async def test_search_finds_tags(async_client, db_session):
    """Trouve dans les tags iconographiques."""
    page_id = await _index_page(db_session, tags="apocalypse sceau martyrs")

    resp = await async_client.get("/api/v1/search?q=apocalypse")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any(r["page_id"] == page_id for r in results)
