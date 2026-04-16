"""
Configuration globale de la plateforme, chargée depuis les variables d'environnement.

Utilise pydantic-settings (CLAUDE.md §2, §7) :
  - les valeurs sont lues depuis os.environ / fichier .env au moment de l'instanciation
  - l'objet `settings` est importé partout dans l'application
  - dans les tests : monkeypatch.setattr(config, "settings", ...) pour surcharger
"""
# 1. stdlib
from pathlib import Path

# 2. third-party
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Racine du dépôt — résolue depuis l'emplacement absolu de ce fichier.
# config.py se trouve dans backend/app/ ; 3 parents remontent à la racine.
# .resolve() garantit un chemin absolu même si __file__ est relatif au CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Paramètres d'application lus depuis les variables d'environnement.

    Toutes les clés API sont optionnelles (None si non configurées).
    Elles ne sont jamais loguées ni exportées (R06).
    """

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # ── Serveur ──────────────────────────────────────────────────────────────
    base_url: str = "http://localhost:8000"
    data_dir: Path = Path("data")
    cors_origins: list[str] = ["*"]

    # ── Chemins des ressources statiques ─────────────────────────────────────
    # Calculés depuis la racine du dépôt ; surchargeables via variables d'env.
    profiles_dir: Path = _REPO_ROOT / "profiles"
    prompts_dir: Path = _REPO_ROOT / "prompts"

    # ── Base de données ───────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./iiif_studio.db"

    # ── Pipeline IA ────────────────────────────────────────────────────────────
    ai_max_concurrent: int = 3  # jobs IA simultanés par corpus run

    # ── Fournisseurs IA (R06 — clés depuis l'environnement uniquement) ────────
    # Chaque clé est optionnelle. Le backend détecte automatiquement quels
    # providers sont disponibles selon les clés présentes. Pas de AI_PROVIDER
    # global : le provider est choisi par corpus depuis l'interface.
    google_ai_studio_api_key: str | None = None
    vertex_service_account_json: str | None = None
    mistral_api_key: str | None = None


settings: Settings = Settings()
