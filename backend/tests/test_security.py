"""
Tests de sécurité — Sprint F1 + Sprint Fix 1.

Vérifie que toutes les vulnérabilités identifiées sont corrigées :
- Path traversal sur profiles, slug, folio_label, frontend serving
- Path traversal sur image_master_path dans le job_runner
- SSRF sur manifest_url
- Validation des entrées (taille, format)
"""
# 1. stdlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# 2. third-party — fixtures API
from tests.conftest_api import async_client, db_session  # noqa: F401

# 3. local — job_runner path traversal tests
import app.models  # noqa: F401
import app.services.job_runner as job_runner_module
from app.models.corpus import CorpusModel, ManuscriptModel, PageModel
from app.models.database import Base
from app.models.job import JobModel
from app.models.model_config_db import ModelConfigDB
from app.services.job_runner import _run_job_impl


# ---------------------------------------------------------------------------
# Path traversal — profiles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_path_traversal_dotdot(async_client):
    """Un profile_id contenant '..' doit être rejeté (400)."""
    resp = await async_client.get("/api/v1/profiles/..passwd")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_profile_path_traversal_slash(async_client):
    """Un profile_id avec un slash (même encodé) doit être rejeté (400 ou 404)."""
    # FastAPI normalise les chemins, donc un slash dans l'ID ne sera pas transmis.
    # On teste avec un ID contenant des caractères spéciaux interdits.
    resp = await async_client.get("/api/v1/profiles/UPPER_CASE")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_profile_path_traversal_special_chars(async_client):
    """Un profile_id avec des caractères spéciaux doit être rejeté."""
    resp = await async_client.get("/api/v1/profiles/test@profile")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_profile_valid_id_not_found(async_client):
    """Un profile_id valide mais inexistant retourne 404 (pas 400)."""
    resp = await async_client.get("/api/v1/profiles/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Path traversal — corpus slug
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_corpus_slug_path_traversal(async_client):
    """Un slug avec ../ doit être rejeté par la validation Pydantic."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "../../malicious",
        "title": "Test",
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_corpus_slug_with_spaces(async_client):
    """Un slug avec des espaces doit être rejeté."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "my corpus",
        "title": "Test",
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_corpus_slug_uppercase(async_client):
    """Un slug avec des majuscules doit être rejeté (lowercase only)."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "MyCorpus",
        "title": "Test",
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_corpus_slug_valid(async_client):
    """Un slug valide doit être accepté."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "my-corpus-01",
        "title": "Test",
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_corpus_slug_empty(async_client):
    """Un slug vide doit être rejeté."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "",
        "title": "Test",
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_corpus_title_too_long(async_client):
    """Un titre trop long (>256 chars) doit être rejeté."""
    resp = await async_client.post("/api/v1/corpora", json={
        "slug": "test-long",
        "title": "x" * 300,
        "profile_id": "medieval-illuminated",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SSRF — manifest_url
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ssrf_localhost(async_client):
    """Un manifest_url pointant vers localhost doit être rejeté."""
    # Créer un corpus d'abord
    create = await async_client.post("/api/v1/corpora", json={
        "slug": "ssrf-test", "title": "SSRF", "profile_id": "medieval-illuminated",
    })
    cid = create.json()["id"]

    resp = await async_client.post(f"/api/v1/corpora/{cid}/ingest/iiif-manifest", json={
        "manifest_url": "http://localhost:8000/secret",
    })
    assert resp.status_code == 400
    assert "interdit" in resp.json()["detail"].lower() or "localhost" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ssrf_metadata_ip(async_client):
    """Un manifest_url vers 169.254.x.x (cloud metadata) doit être rejeté."""
    create = await async_client.post("/api/v1/corpora", json={
        "slug": "ssrf-meta", "title": "SSRF", "profile_id": "medieval-illuminated",
    })
    cid = create.json()["id"]

    resp = await async_client.post(f"/api/v1/corpora/{cid}/ingest/iiif-manifest", json={
        "manifest_url": "http://169.254.169.254/latest/meta-data/",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ssrf_file_scheme(async_client):
    """Un manifest_url avec file:// doit être rejeté."""
    create = await async_client.post("/api/v1/corpora", json={
        "slug": "ssrf-file", "title": "SSRF", "profile_id": "medieval-illuminated",
    })
    cid = create.json()["id"]

    resp = await async_client.post(f"/api/v1/corpora/{cid}/ingest/iiif-manifest", json={
        "manifest_url": "file:///etc/passwd",
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Input validation — search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_query_too_long(async_client):
    """Une requête de recherche >500 chars doit être rejetée."""
    resp = await async_client.get("/api/v1/search", params={"q": "x" * 501})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_query_max_length_ok(async_client):
    """Une requête de recherche de 500 chars doit être acceptée (0 résultat)."""
    resp = await async_client.get("/api/v1/search", params={"q": "x" * 500})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Input validation — model selection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_id_too_long(async_client):
    """Un model_id >256 chars doit être rejeté."""
    create = await async_client.post("/api/v1/corpora", json={
        "slug": "model-test", "title": "T", "profile_id": "medieval-illuminated",
    })
    cid = create.json()["id"]

    resp = await async_client.put(f"/api/v1/corpora/{cid}/model", json={
        "model_id": "x" * 300,
        "provider_type": "google_ai_studio",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Input validation — corrections
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_corrections_restore_negative_version(async_client):
    """restore_to_version < 1 doit être rejeté."""
    resp = await async_client.post("/api/v1/pages/fake-page/corrections", json={
        "restore_to_version": 0,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Path traversal — job_runner (image_master_path)
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def _sec_db():
    """Session SQLite en mémoire pour les tests path traversal."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_traversal_setup(_sec_db, image_path: str) -> dict:
    """Crée un jeu de données complet avec le chemin image fourni."""
    corpus = CorpusModel(
        id=str(uuid.uuid4()), slug="sec-test", title="Sec",
        profile_id="medieval-illuminated", created_at=_NOW, updated_at=_NOW,
    )
    _sec_db.add(corpus)
    await _sec_db.commit()

    ms = ManuscriptModel(
        id=str(uuid.uuid4()), corpus_id=corpus.id, title="MS", total_pages=1,
    )
    _sec_db.add(ms)
    await _sec_db.commit()

    page = PageModel(
        id=str(uuid.uuid4()), manuscript_id=ms.id, folio_label="f001r",
        sequence=1, image_master_path=image_path,
        processing_status="INGESTED",
    )
    _sec_db.add(page)
    await _sec_db.commit()

    model_cfg = ModelConfigDB(
        corpus_id=corpus.id, provider_type="google_ai_studio",
        selected_model_id="gemini-2.0-flash",
        selected_model_display_name="Gemini 2.0 Flash",
        updated_at=_NOW,
    )
    _sec_db.add(model_cfg)
    await _sec_db.commit()

    job = JobModel(
        id=str(uuid.uuid4()), corpus_id=corpus.id, page_id=page.id,
        status="pending", created_at=_NOW,
    )
    _sec_db.add(job)
    await _sec_db.commit()
    return {"job": job, "page": page}


@pytest.mark.asyncio
async def test_path_traversal_dotdot_rejected(_sec_db):
    """image_master_path avec ../../etc/passwd doit provoquer un échec du job."""
    s = await _create_traversal_setup(_sec_db, "../../etc/passwd")

    await _run_job_impl(s["job"].id, _sec_db)
    await _sec_db.refresh(s["job"])

    assert s["job"].status == "failed"
    assert "interdit" in (s["job"].error_message or "").lower() or \
           "hors" in (s["job"].error_message or "").lower()


@pytest.mark.asyncio
async def test_path_traversal_absolute_path_rejected(_sec_db):
    """image_master_path absolu hors data_dir doit provoquer un échec du job."""
    s = await _create_traversal_setup(_sec_db, "/etc/shadow")

    await _run_job_impl(s["job"].id, _sec_db)
    await _sec_db.refresh(s["job"])

    assert s["job"].status == "failed"
    assert "interdit" in (s["job"].error_message or "").lower() or \
           "hors" in (s["job"].error_message or "").lower()


@pytest.mark.asyncio
async def test_path_traversal_symlink_escape_rejected(_sec_db, tmp_path):
    """Un chemin sous data_dir mais avec traversal intermédiaire est rejeté."""
    s = await _create_traversal_setup(
        _sec_db, "data/../../../etc/passwd"
    )

    await _run_job_impl(s["job"].id, _sec_db)
    await _sec_db.refresh(s["job"])

    assert s["job"].status == "failed"
