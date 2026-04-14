"""
Application FastAPI — point d'entrée de IIIF Studio.

Tous les endpoints sont sous /api/v1/ (R10).
CORS ouvert pour le développement local (origins=["*"]).
La BDD SQLite est créée automatiquement au démarrage (lifespan).
"""
# 1. stdlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# 2. third-party
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

# 3. local — on importe les modèles pour que Base.metadata les connaisse
import app.models  # noqa: F401  (enregistrement des modèles SQLAlchemy)
from app.api.v1 import corpora, export, ingest, jobs, manuscripts, models_api, pages, profiles, search
from app.models.database import Base, engine

logger = logging.getLogger(__name__)


def _migrate_model_configs(connection) -> None:
    """Ajoute la colonne supports_vision si absente (migration BDD existantes)."""
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    columns = {c["name"] for c in inspector.get_columns("model_configs")}
    if "supports_vision" not in columns:
        connection.execute(
            text("ALTER TABLE model_configs ADD COLUMN supports_vision BOOLEAN NOT NULL DEFAULT 1")
        )
        logger.info("Migration : colonne supports_vision ajoutée à model_configs")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Crée les tables SQLite au démarrage, libère l'engine à l'arrêt."""
    from app.config import settings

    # ── Diagnostic des chemins au démarrage ──────────────────────────────────
    # Ces logs apparaissent dans la console HuggingFace et permettent de
    # diagnostiquer instantanément tout problème de chemin en production.
    logger.info(
        "Démarrage IIIF Studio — chemins configurés",
        extra={
            "profiles_dir": str(settings.profiles_dir),
            "profiles_dir_ok": settings.profiles_dir.is_dir(),
            "prompts_dir": str(settings.prompts_dir),
            "prompts_dir_ok": settings.prompts_dir.is_dir(),
            "data_dir": str(settings.data_dir),
            "data_dir_ok": settings.data_dir.exists(),
        },
    )
    if not settings.profiles_dir.is_dir():
        logger.error(
            "ERREUR CRITIQUE : profiles_dir introuvable au démarrage. "
            "GET /api/v1/profiles retournera []. "
            "Vérifier PROFILES_DIR ou la structure du container.",
            extra={"profiles_dir": str(settings.profiles_dir)},
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration : ajouter supports_vision aux model_configs existantes
        # (create_all ne fait pas d'ALTER TABLE sur les tables existantes)
        await conn.run_sync(_migrate_model_configs)
    logger.info("Tables SQLite initialisées")
    yield
    await engine.dispose()
    logger.info("Engine SQLite fermé")


app = FastAPI(
    title="IIIF Studio",
    description="Plateforme générique de génération d'éditions savantes augmentées",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (configurable via CORS_ORIGINS ; défaut : ["*"] pour le dev) ─────────
from app.config import settings as _settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (préfixe /api/v1/ — R10) ─────────────────────────────────────────
_V1_PREFIX = "/api/v1"

app.include_router(corpora.router, prefix=_V1_PREFIX)
app.include_router(manuscripts.router, prefix=_V1_PREFIX)
app.include_router(pages.router, prefix=_V1_PREFIX)
app.include_router(export.router, prefix=_V1_PREFIX)
app.include_router(profiles.router, prefix=_V1_PREFIX)
app.include_router(jobs.router, prefix=_V1_PREFIX)
app.include_router(ingest.router, prefix=_V1_PREFIX)
app.include_router(models_api.router, prefix=_V1_PREFIX)
app.include_router(search.router, prefix=_V1_PREFIX)

# ── Serving frontend SPA (production) ou redirect /docs (dev) ────────────────
_STATIC_DIR = Path("/app/static")


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
async def serve_frontend(full_path: str) -> FileResponse | RedirectResponse:
    """En production sert le frontend React (SPA). En dev redirige vers /docs."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail=f"Endpoint not found: /{full_path}")
    if _STATIC_DIR.is_dir():
        candidate = (_STATIC_DIR / full_path).resolve()
        # Empêcher le path traversal : le fichier résolu doit être sous _STATIC_DIR
        if candidate.is_file() and str(candidate).startswith(str(_STATIC_DIR.resolve())):
            return FileResponse(candidate)
        index = _STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
    return RedirectResponse(url="/docs")
