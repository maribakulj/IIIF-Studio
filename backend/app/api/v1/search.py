"""
Endpoint de recherche plein texte (R10 — préfixe /api/v1/).

GET  /api/v1/search?q={query}
POST /api/v1/search/reindex

Implémentation indexée : les données sont dans la table page_search,
mises à jour à chaque écriture de master.json.
"""
# 1. stdlib
import logging

# 2. third-party
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# 3. local
from app import config as _config_module
from app.models.database import get_db
from app.services.search.indexer import reindex_all, search_pages

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchResult(BaseModel):
    page_id: str
    folio_label: str
    manuscript_id: str
    excerpt: str
    score: int
    corpus_profile: str


class ReindexResponse(BaseModel):
    pages_indexed: int


@router.get("/search", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResult]:
    """Recherche plein texte dans l'index des pages analysées."""
    hits = await search_pages(db, q, limit)
    logger.info("Recherche exécutée", extra={"q": q, "results": len(hits)})
    return [SearchResult(**h) for h in hits]


@router.post("/search/reindex", response_model=ReindexResponse)
async def reindex(db: AsyncSession = Depends(get_db)) -> ReindexResponse:
    """Reconstruit l'index de recherche depuis les fichiers master.json."""
    count = await reindex_all(db, _config_module.settings.data_dir)
    return ReindexResponse(pages_indexed=count)
