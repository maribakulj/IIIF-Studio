"""
Endpoints de lecture des profils de corpus (R10 — préfixe /api/v1/).

GET  /api/v1/profiles
GET  /api/v1/profiles/{profile_id}

Les profils sont des fichiers JSON dans profiles/ (racine du dépôt).
Ils sont validés par CorpusProfile avant d'être retournés.
"""
# 1. stdlib
import asyncio
import json
import logging
import re
from pathlib import Path

# 2. third-party
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

# 3. local
from app.config import settings
from app.schemas.corpus_profile import CorpusProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])

_profiles_cache: dict[str, CorpusProfile] | None = None


def _load_all_profiles() -> dict[str, CorpusProfile]:
    """Charge tous les profils depuis le disque (cache singleton)."""
    global _profiles_cache
    if _profiles_cache is not None:
        return _profiles_cache

    result: dict[str, CorpusProfile] = {}
    if settings.profiles_dir.is_dir():
        for path in sorted(settings.profiles_dir.glob("*.json")):
            profile = _load_profile(path)
            if profile is not None:
                result[profile.profile_id] = profile
    else:
        logger.warning("profiles_dir introuvable : %s", settings.profiles_dir)

    _profiles_cache = result
    return _profiles_cache


def _load_profile(path: Path) -> CorpusProfile | None:
    """Charge et valide un fichier de profil JSON. Retourne None si invalide."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CorpusProfile.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Profil invalide ignoré", extra={"path": str(path), "error": str(exc)})
        return None


@router.get("", response_model=list[dict])
async def list_profiles() -> list[dict]:
    """Retourne tous les profils valides du dossier profiles/."""
    profiles = _load_all_profiles()
    return [p.model_dump() for p in profiles.values()]


_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@router.get("/{profile_id}", response_model=dict)
async def get_profile(profile_id: str) -> dict:
    """Retourne un profil par son id (nom du fichier sans extension)."""
    if not _SAFE_ID_RE.match(profile_id):
        raise HTTPException(status_code=400, detail="profile_id invalide")

    profiles = _load_all_profiles()
    profile = profiles.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    return profile.model_dump()
