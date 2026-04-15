"""
Test d'integration du pipeline complet : ingestion -> analyse IA -> exports.

Valide la chaine sans appel reseau (provider IA et fetch image mockes).
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.database import Base
from app.models.corpus import CorpusModel, ManuscriptModel, PageModel
from app.models.job import JobModel
from app.models.model_config_db import ModelConfigDB
from app.models.page_search import PageSearchIndex


_FAKE_AI_RESPONSE = json.dumps({
    "layout": {
        "regions": [
            {"id": "r1", "type": "text_block", "bbox": [100, 200, 800, 600], "confidence": 0.92}
        ]
    },
    "ocr": {
        "diplomatic_text": "Incipit liber primus de apocalypsi",
        "blocks": [],
        "lines": [],
        "language": "la",
        "confidence": 0.85,
        "uncertain_segments": []
    }
})

# Minimal 1x1 white JPEG
_FAKE_JPEG = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
    0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
    0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
    0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
    0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0x7B, 0x94,
    0x11, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0xD9,
])


@pytest.fixture
async def pipeline_db():
    """BDD en memoire avec toutes les tables creees."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def pipeline_fixtures(pipeline_db, tmp_path):
    """Cree corpus + manuscrit + page + model config + job en BDD."""
    db = pipeline_db
    corpus_id = str(uuid.uuid4())
    ms_id = str(uuid.uuid4())
    page_id = "test-corpus-f001r"
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    corpus = CorpusModel(
        id=corpus_id, slug="test-corpus", title="Test",
        profile_id="medieval-illuminated", created_at=now, updated_at=now,
    )
    ms = ManuscriptModel(
        id=ms_id, corpus_id=corpus_id, title="Ms Test", total_pages=1,
    )
    page = PageModel(
        id=page_id, manuscript_id=ms_id, folio_label="f001r", sequence=1,
        iiif_service_url="https://example.com/iiif/image1",
        processing_status="INGESTED",
    )
    model_config = ModelConfigDB(
        corpus_id=corpus_id, provider_type="google_ai_studio",
        selected_model_id="gemini-2.0-flash",
        selected_model_display_name="Gemini Flash",
        supports_vision=True, updated_at=now,
    )
    job = JobModel(
        id=job_id, corpus_id=corpus_id, page_id=page_id,
        status="pending", created_at=now,
    )

    db.add_all([corpus, ms, page, model_config, job])
    await db.commit()

    return {
        "db": db,
        "corpus_id": corpus_id, "ms_id": ms_id, "page_id": page_id,
        "job_id": job_id, "data_dir": tmp_path,
    }


@pytest.mark.asyncio
async def test_full_pipeline(pipeline_fixtures, tmp_path):
    """Le pipeline complet produit master.json, ai_raw.json, alto.xml et indexe la page."""
    fx = pipeline_fixtures
    db = fx["db"]

    import app.config as config_mod

    # Mock settings to use tmp_path as data_dir
    original_data_dir = config_mod.settings.data_dir
    original_profiles_dir = config_mod.settings.profiles_dir
    config_mod.settings.__dict__["data_dir"] = tmp_path

    # Ensure profiles_dir points to the real profiles directory
    # (profiles_dir is resolved from _REPO_ROOT in config.py and should
    #  already point to the correct location, but we set it explicitly
    #  for safety in case tests run from a different CWD.)
    repo_root = Path(__file__).resolve().parent.parent.parent
    real_profiles_dir = repo_root / "profiles"
    if real_profiles_dir.exists():
        config_mod.settings.__dict__["profiles_dir"] = real_profiles_dir

    # Mock the AI provider and image fetcher
    mock_provider = MagicMock()
    mock_provider.generate_content.return_value = _FAKE_AI_RESPONSE

    try:
        with patch(
            "app.services.job_runner.fetch_ai_derivative_bytes",
            return_value=(_FAKE_JPEG, 1500, 1000),
        ), patch(
            "app.services.ai.model_registry.get_provider",
            return_value=mock_provider,
        ):
            from app.services.job_runner import _run_job_impl
            await _run_job_impl(fx["job_id"], db)
    finally:
        config_mod.settings.__dict__["data_dir"] = original_data_dir
        config_mod.settings.__dict__["profiles_dir"] = original_profiles_dir

    # -- Assertions ----------------------------------------------------------
    # Job should be done
    job = await db.get(JobModel, fx["job_id"])
    assert job.status == "done", f"Job status: {job.status}, error: {job.error_message}"

    # Page should be ANALYZED
    page = await db.get(PageModel, fx["page_id"])
    assert page.processing_status == "ANALYZED"

    # Files should exist
    page_dir = tmp_path / "corpora" / "test-corpus" / "pages" / "f001r"
    assert (page_dir / "master.json").exists(), "master.json not written"
    assert (page_dir / "ai_raw.json").exists(), "ai_raw.json not written"
    assert (page_dir / "alto.xml").exists(), "alto.xml not written"

    # master.json should be valid
    master_data = json.loads((page_dir / "master.json").read_text())
    assert master_data["page_id"] == fx["page_id"]
    assert len(master_data["layout"]["regions"]) == 1

    # Search index should be populated
    search_entry = await db.get(PageSearchIndex, fx["page_id"])
    assert search_entry is not None
    assert "Incipit" in search_entry.diplomatic_text
