"""
Chargement et rendu des templates de prompts depuis le système de fichiers (R04).

Les prompts vivent dans prompts/{profile_id}/{famille}_v{n}.txt.
Le code charge le fichier, substitue les variables {{nom}}, envoie à l'API.
"""
# 1. stdlib
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def _read_template(path_str: str) -> str:
    """Lit un template depuis le disque avec cache LRU."""
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Template introuvable : {path_str}")
    return path.read_text(encoding="utf-8")


def load_and_render_prompt(template_path: str | Path, context: dict[str, str]) -> str:
    """Charge un template de prompt depuis un fichier et substitue les variables.

    Les variables du template ont la forme {{nom_variable}}.
    Toutes les clés de `context` sont substituées ; les clés absentes du template
    sont ignorées silencieusement.

    Args:
        template_path: chemin vers le fichier template (.txt), absolu ou relatif au CWD.
        context: dictionnaire {nom_variable: valeur} pour la substitution.

    Returns:
        Texte du prompt avec toutes les variables substituées.

    Raises:
        FileNotFoundError: si le fichier template n'existe pas.
    """
    path = Path(template_path).resolve()

    template = _read_template(str(path))

    rendered = template
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", value)

    # Vérifier qu'il ne reste pas de variables non résolues (CLAUDE.md §8)
    unresolved = re.findall(r"\{\{\w+\}\}", rendered)
    if unresolved:
        raise ValueError(f"Variables non résolues dans le prompt : {unresolved}")

    logger.debug(
        "Prompt chargé et rendu",
        extra={"template": str(path), "variables": list(context.keys())},
    )
    return rendered
