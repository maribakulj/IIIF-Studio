"""
Écriture des fichiers ai_raw.json et master.json (R02, R05).

Règle R05 non négociable :
  1. ai_raw.json est TOUJOURS écrit en premier.
  2. master.json n'est écrit QUE si le parsing et la validation Pydantic ont réussi.
"""
# 1. stdlib
import json
import logging
from pathlib import Path

# 3. local
from app.schemas.page_master import PageMaster

logger = logging.getLogger(__name__)


def write_ai_raw(raw_text: str, output_path: Path) -> None:
    """Écrit la réponse brute de l'IA dans ai_raw.json (R05).

    Toujours appelé AVANT toute tentative de parsing.
    Le contenu est enveloppé dans un objet JSON pour garantir un fichier valide,
    même si la réponse IA n'est pas du JSON.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"response_text": raw_text}
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Écriture ai_raw.json échouée", extra={"path": str(output_path), "error": str(exc)})
        raise
    logger.info("ai_raw.json écrit", extra={"path": str(output_path)})


def write_master_json(page_master: PageMaster, output_path: Path) -> None:
    """Écrit le PageMaster validé dans master.json (R02, R05).

    N'est appelé QUE si le parsing et la validation Pydantic ont réussi.
    Crée les dossiers parents si nécessaire.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            page_master.model_dump_json(indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Écriture master.json échouée", extra={"path": str(output_path), "error": str(exc)})
        raise
    logger.info("master.json écrit", extra={"path": str(output_path)})
