"""
Parsing et validation de la réponse brute de l'IA → layout dict + OCRResult.

Comportement :
- JSON non parseable       → ParseError (toute la page échoue)
- Région avec bbox invalide → région ignorée + log (la page continue)
- OCR invalide             → OCRResult() par défaut + log (la page continue)

Le parser est tolérant : il extrait le premier objet JSON valide du texte
même si l'IA ajoute du texte autour, des balises Markdown, des virgules
en trop, ou des échappements Unicode cassés.
"""
# 1. stdlib
import json
import logging
import re

# 2. third-party
from pydantic import ValidationError

# 3. local
from app.schemas.page_master import OCRResult, Region

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Levée si la réponse de l'IA est un JSON invalide ou structurellement incorrecte."""


def _extract_json_object(text: str) -> str:
    """Extrait le premier objet JSON { ... } complet du texte.

    Les VLMs renvoient souvent du texte avant/après le JSON, ou plusieurs
    blocs JSON concaténés. Cette fonction trouve le premier '{' et compte
    les accolades pour trouver le '}' fermant correspondant, en ignorant
    les accolades à l'intérieur des chaînes.
    """
    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Pas de fermeture trouvée — retourner depuis le premier '{'
    return text[start:]


def _fix_common_json_issues(text: str) -> str:
    """Corrige les erreurs JSON courantes des VLMs.

    - Trailing commas avant } ou ]
    - Échappements Unicode invalides (\\uXXXX incomplets)
    """
    # Trailing commas : ,} ou ,]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Échappements unicode invalides — remplacer par un espace
    text = re.sub(r"\\u(?![0-9a-fA-F]{4})[^\"]*", " ", text)
    return text


def _try_parse_json(text: str) -> dict | None:
    """Tente de parser du JSON, avec nettoyage progressif en cas d'échec."""
    # Tentative 1 : tel quel
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentative 2 : corrections courantes
    fixed = _fix_common_json_issues(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def parse_ai_response(raw_text: str) -> tuple[dict, OCRResult]:
    """Parse la réponse textuelle de l'IA en layout dict + OCRResult validés.

    Les régions avec bbox invalide sont ignorées individuellement (loguées) sans
    faire échouer toute la page. Un JSON non parseable lève ParseError.

    Gère les balises Markdown (```json ... ```) que certains modèles ajoutent
    malgré les instructions, ainsi que le texte avant/après le JSON et les
    erreurs de formatage courantes des VLMs.

    Args:
        raw_text: texte brut retourné par l'IA (censé être du JSON strict).

    Returns:
        Tuple (layout_dict, ocr_result) où layout_dict = {"regions": [...]}.

    Raises:
        ParseError: si le texte n'est pas du JSON valide ou pas un objet JSON.
    """
    # Suppression des balises Markdown éventuelles
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])

    # Extraction du premier objet JSON (ignore le texte autour)
    text = _extract_json_object(text)

    data = _try_parse_json(text)

    if data is None:
        raise ParseError(
            f"Réponse IA non parseable en JSON après nettoyage. "
            f"Début du texte brut : {raw_text[:300]!r}"
        )

    if not isinstance(data, dict):
        raise ParseError(
            f"Réponse IA invalide — objet JSON attendu, reçu : {type(data).__name__}"
        )

    # ── Layout / régions ────────────────────────────────────────────────────
    raw_layout = data.get("layout")
    raw_regions: list = []
    if isinstance(raw_layout, dict):
        raw_regions = raw_layout.get("regions") or []

    valid_regions: list[dict] = []
    for i, raw_region in enumerate(raw_regions):
        try:
            region = Region.model_validate(raw_region)
            valid_regions.append(region.model_dump())
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Région ignorée — bbox ou champ invalide",
                extra={"index": i, "region": raw_region, "error": str(exc)},
            )

    layout: dict = {"regions": valid_regions}

    # ── OCR ─────────────────────────────────────────────────────────────────
    raw_ocr = data.get("ocr")
    ocr: OCRResult
    if raw_ocr and isinstance(raw_ocr, dict):
        try:
            ocr = OCRResult.model_validate(raw_ocr)
        except ValidationError as exc:
            logger.warning(
                "OCR invalide — utilisation des valeurs par défaut",
                extra={"error": str(exc)},
            )
            ocr = OCRResult()
    else:
        ocr = OCRResult()

    logger.info(
        "Réponse IA parsée",
        extra={
            "regions_total": len(raw_regions),
            "regions_valides": len(valid_regions),
            "regions_ignorees": len(raw_regions) - len(valid_regions),
            "ocr_confidence": ocr.confidence,
        },
    )
    return layout, ocr
