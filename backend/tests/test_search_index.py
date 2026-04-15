"""
Tests pour le service d'indexation et de recherche (page_search + indexer).
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — enregistrement des modeles
from app.models.database import Base
from app.schemas.page_master import PageMaster
from app.services.search.indexer import (
    _extract_tags,
    _normalize,
    index_page,
    reindex_all,
    search_pages,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    """Session AsyncSession sur une BDD SQLite en memoire."""
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_master(
    page_id: str = "test-ms-001r",
    corpus_profile: str = "medieval-illuminated",
    manuscript_id: str = "test-ms",
    folio_label: str = "001r",
    diplomatic_text: str = "Explicit liber primus",
    translation_fr: str = "Fin du premier livre",
    tags: list[str] | None = None,
) -> PageMaster:
    """Construit un PageMaster minimal valide pour les tests."""
    extensions: dict = {}
    if tags:
        extensions["iconography"] = [{"region_id": "r1", "tags": tags}]

    data = {
        "schema_version": "1.0",
        "page_id": page_id,
        "corpus_profile": corpus_profile,
        "manuscript_id": manuscript_id,
        "folio_label": folio_label,
        "sequence": 1,
        "image": {
            "master": "https://example.com/image.jpg",
            "width": 3000,
            "height": 4000,
        },
        "layout": {
            "regions": [
                {
                    "id": "r1",
                    "type": "text_block",
                    "bbox": [100, 100, 500, 500],
                    "confidence": 0.9,
                }
            ]
        },
        "ocr": {
            "diplomatic_text": diplomatic_text,
            "language": "la",
            "confidence": 0.8,
        },
        "translation": {"fr": translation_fr, "en": ""},
        "extensions": extensions,
    }
    return PageMaster.model_validate(data)


# ── Tests _normalize ──────────────────────────────────────────────────────────


class TestNormalize:
    def test_lowercase(self):
        assert _normalize("HELLO") == "hello"

    def test_accent_removal(self):
        assert _normalize("éàü") == "eau"

    def test_combined(self):
        assert _normalize("Début du Récit") == "debut du recit"

    def test_empty(self):
        assert _normalize("") == ""


# ── Tests _extract_tags ───────────────────────────────────────────────────────


class TestExtractTags:
    def test_with_tags(self):
        master = _make_master(tags=["apocalypse", "martyrs", "autel"])
        result = _extract_tags(master)
        assert "apocalypse" in result
        assert "martyrs" in result
        assert "autel" in result

    def test_no_tags(self):
        master = _make_master(tags=None)
        result = _extract_tags(master)
        assert result == ""

    def test_empty_extensions(self):
        master = _make_master()
        # Force extensions to empty dict
        data = master.model_dump(mode="json")
        data["extensions"] = {}
        m = PageMaster.model_validate(data)
        assert _extract_tags(m) == ""


# ── Tests index_page ─────────────────────────────────────────────────────────


class TestIndexPage:
    @pytest.mark.asyncio
    async def test_index_new_page(self, db: AsyncSession):
        master = _make_master()
        await index_page(db, master)
        await db.commit()

        # Verify it was inserted
        from app.models.page_search import PageSearchIndex

        row = await db.get(PageSearchIndex, master.page_id)
        assert row is not None
        assert row.page_id == "test-ms-001r"
        assert row.diplomatic_text == "Explicit liber primus"
        assert row.translation_fr == "Fin du premier livre"
        assert row.manuscript_id == "test-ms"

    @pytest.mark.asyncio
    async def test_index_update_existing(self, db: AsyncSession):
        master = _make_master(diplomatic_text="version 1")
        await index_page(db, master)
        await db.commit()

        # Update with new content
        master2 = _make_master(diplomatic_text="version 2")
        await index_page(db, master2)
        await db.commit()

        from app.models.page_search import PageSearchIndex

        row = await db.get(PageSearchIndex, master.page_id)
        assert row is not None
        assert row.diplomatic_text == "version 2"

    @pytest.mark.asyncio
    async def test_index_page_without_ocr(self, db: AsyncSession):
        data = {
            "schema_version": "1.0",
            "page_id": "no-ocr-page",
            "corpus_profile": "medieval-illuminated",
            "manuscript_id": "test-ms",
            "folio_label": "001r",
            "sequence": 1,
            "image": {
                "master": "https://example.com/image.jpg",
                "width": 3000,
                "height": 4000,
            },
            "layout": {"regions": []},
            "ocr": None,
            "translation": None,
        }
        master = PageMaster.model_validate(data)
        await index_page(db, master)
        await db.commit()

        from app.models.page_search import PageSearchIndex

        row = await db.get(PageSearchIndex, "no-ocr-page")
        assert row is not None
        assert row.diplomatic_text == ""
        assert row.translation_fr == ""

    @pytest.mark.asyncio
    async def test_index_page_with_tags(self, db: AsyncSession):
        master = _make_master(tags=["sceau", "martyrs"])
        await index_page(db, master)
        await db.commit()

        from app.models.page_search import PageSearchIndex

        row = await db.get(PageSearchIndex, master.page_id)
        assert row is not None
        assert "sceau" in row.tags
        assert "martyrs" in row.tags


# ── Tests search_pages ────────────────────────────────────────────────────────


class TestSearchPages:
    @pytest.mark.asyncio
    async def test_search_finds_diplomatic_text(self, db: AsyncSession):
        master = _make_master(diplomatic_text="Explicit liber primus incipit")
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "liber")
        assert len(hits) == 1
        assert hits[0]["page_id"] == "test-ms-001r"
        assert hits[0]["score"] >= 1

    @pytest.mark.asyncio
    async def test_search_finds_translation(self, db: AsyncSession):
        master = _make_master(translation_fr="Fin du premier livre")
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "premier")
        assert len(hits) == 1
        assert hits[0]["page_id"] == "test-ms-001r"

    @pytest.mark.asyncio
    async def test_search_finds_tags(self, db: AsyncSession):
        master = _make_master(tags=["apocalypse", "martyrs"])
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "apocalypse")
        assert len(hits) == 1

    @pytest.mark.asyncio
    async def test_accent_insensitive_search(self, db: AsyncSession):
        master = _make_master(translation_fr="Début du récit apocalyptique")
        await index_page(db, master)
        await db.commit()

        # Search without accents
        hits = await search_pages(db, "debut")
        assert len(hits) == 1

        # Search with accents
        hits = await search_pages(db, "début")
        assert len(hits) == 1

        # Search with wrong accents
        hits = await search_pages(db, "recit")
        assert len(hits) == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, db: AsyncSession):
        master = _make_master(diplomatic_text="Explicit Liber Primus")
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "EXPLICIT")
        assert len(hits) == 1

        hits = await search_pages(db, "explicit")
        assert len(hits) == 1

    @pytest.mark.asyncio
    async def test_empty_query_returns_nothing(self, db: AsyncSession):
        master = _make_master()
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "")
        assert hits == []

        hits = await search_pages(db, "   ")
        assert hits == []

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, db: AsyncSession):
        master = _make_master(diplomatic_text="Explicit liber primus")
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "zzzznonexistent")
        assert hits == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_score(self, db: AsyncSession):
        # Page with many occurrences
        master1 = _make_master(
            page_id="ms-high",
            folio_label="001r",
            diplomatic_text="liber liber liber liber liber",
        )
        # Page with fewer occurrences
        master2 = _make_master(
            page_id="ms-low",
            folio_label="002r",
            diplomatic_text="liber primus",
        )
        await index_page(db, master1)
        await index_page(db, master2)
        await db.commit()

        hits = await search_pages(db, "liber")
        assert len(hits) == 2
        assert hits[0]["page_id"] == "ms-high"
        assert hits[0]["score"] > hits[1]["score"]

    @pytest.mark.asyncio
    async def test_limit_parameter(self, db: AsyncSession):
        # Index 5 pages
        for i in range(5):
            master = _make_master(
                page_id=f"ms-{i:03d}r",
                folio_label=f"{i:03d}r",
                diplomatic_text="common text shared across all pages",
            )
            await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "common", limit=3)
        assert len(hits) == 3

    @pytest.mark.asyncio
    async def test_excerpt_is_populated(self, db: AsyncSession):
        master = _make_master(diplomatic_text="Before context Explicit liber primus after context")
        await index_page(db, master)
        await db.commit()

        hits = await search_pages(db, "liber")
        assert len(hits) == 1
        assert "liber" in hits[0]["excerpt"].lower()

    @pytest.mark.asyncio
    async def test_search_across_multiple_fields(self, db: AsyncSession):
        """A page matching in multiple fields should have a higher score."""
        # Page matching in both diplomatic and translation
        master1 = _make_master(
            page_id="ms-multi",
            diplomatic_text="liber primus",
            translation_fr="liber premier",
        )
        # Page matching in diplomatic only
        master2 = _make_master(
            page_id="ms-single",
            diplomatic_text="liber primus",
            translation_fr="rien a voir",
        )
        await index_page(db, master1)
        await index_page(db, master2)
        await db.commit()

        hits = await search_pages(db, "liber")
        assert len(hits) == 2
        assert hits[0]["page_id"] == "ms-multi"
        assert hits[0]["score"] > hits[1]["score"]


# ── Tests reindex_all ─────────────────────────────────────────────────────────


class TestReindexAll:
    @pytest.mark.asyncio
    async def test_reindex_from_filesystem(self, db: AsyncSession, tmp_path: Path):
        """reindex_all should read master.json files and populate the index."""
        # Create a fake corpus directory structure
        corpus_dir = tmp_path / "corpora" / "test-ms" / "pages" / "001r"
        corpus_dir.mkdir(parents=True)

        master_data = {
            "schema_version": "1.0",
            "page_id": "test-ms-001r",
            "corpus_profile": "medieval-illuminated",
            "manuscript_id": "test-ms",
            "folio_label": "001r",
            "sequence": 1,
            "image": {
                "master": "https://example.com/image.jpg",
                "width": 3000,
                "height": 4000,
            },
            "layout": {"regions": []},
            "ocr": {
                "diplomatic_text": "Explicit liber primus",
                "language": "la",
                "confidence": 0.8,
            },
            "translation": {"fr": "Fin du premier livre", "en": ""},
        }
        (corpus_dir / "master.json").write_text(
            json.dumps(master_data), encoding="utf-8"
        )

        count = await reindex_all(db, tmp_path)
        assert count == 1

        # Verify the page was indexed
        hits = await search_pages(db, "liber")
        assert len(hits) == 1
        assert hits[0]["page_id"] == "test-ms-001r"

    @pytest.mark.asyncio
    async def test_reindex_skips_invalid_files(self, db: AsyncSession, tmp_path: Path):
        """reindex_all should skip invalid master.json files gracefully."""
        corpus_dir = tmp_path / "corpora" / "test-ms" / "pages" / "bad"
        corpus_dir.mkdir(parents=True)

        # Write invalid JSON
        (corpus_dir / "master.json").write_text("not valid json", encoding="utf-8")

        count = await reindex_all(db, tmp_path)
        assert count == 0

    @pytest.mark.asyncio
    async def test_reindex_empty_dir(self, db: AsyncSession, tmp_path: Path):
        """reindex_all on an empty data dir should return 0."""
        count = await reindex_all(db, tmp_path)
        assert count == 0

    @pytest.mark.asyncio
    async def test_reindex_multiple_pages(self, db: AsyncSession, tmp_path: Path):
        """reindex_all with multiple valid master.json files."""
        for folio in ["001r", "002r", "003r"]:
            page_dir = tmp_path / "corpora" / "test-ms" / "pages" / folio
            page_dir.mkdir(parents=True)
            data = {
                "schema_version": "1.0",
                "page_id": f"test-ms-{folio}",
                "corpus_profile": "medieval-illuminated",
                "manuscript_id": "test-ms",
                "folio_label": folio,
                "sequence": int(folio[:3]),
                "image": {
                    "master": "https://example.com/image.jpg",
                    "width": 3000,
                    "height": 4000,
                },
                "layout": {"regions": []},
                "ocr": {
                    "diplomatic_text": f"Text for folio {folio}",
                    "language": "la",
                    "confidence": 0.8,
                },
            }
            (page_dir / "master.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

        count = await reindex_all(db, tmp_path)
        assert count == 3
