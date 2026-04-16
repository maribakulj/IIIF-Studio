"""
Provider Google AI Studio — authentification via GOOGLE_AI_STUDIO_API_KEY.
"""
# 1. stdlib
import logging
import os

# 2. third-party
from google import genai
from google.genai import types

# 3. local
from app.schemas.model_config import ModelInfo, ProviderType
from app.services.ai.base import AIProvider, is_vision_model

logger = logging.getLogger(__name__)

_ENV_KEY = "GOOGLE_AI_STUDIO_API_KEY"


class GoogleAIProvider(AIProvider):
    """Provider Google AI Studio (clé API GOOGLE_AI_STUDIO_API_KEY)."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GOOGLE_AI_STUDIO

    def is_configured(self) -> bool:
        return bool(os.environ.get(_ENV_KEY))

    def _get_client(self) -> genai.Client:
        """Retourne un client cached (réutilise la connexion SSL)."""
        if self._client is None:
            self._client = genai.Client(api_key=os.environ[_ENV_KEY])
        return self._client

    def list_models(self) -> list[ModelInfo]:
        if not self.is_configured():
            raise RuntimeError(f"Variable d'environnement manquante : {_ENV_KEY}")

        client = self._get_client()
        result: list[ModelInfo] = []

        for model in client.models.list():
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue

            result.append(ModelInfo(
                model_id=model.name,
                display_name=getattr(model, "display_name", model.name),
                provider=self.provider_type,
                supports_vision=is_vision_model(model),
                input_token_limit=getattr(model, "input_token_limit", None),
                output_token_limit=getattr(model, "output_token_limit", None),
            ))

        logger.info(
            "Google AI Studio models fetched",
            extra={"provider": self.provider_type, "count": len(result)},
        )
        return result

    def generate_content(self, image_bytes: bytes, prompt: str, model_id: str, supports_vision: bool = True) -> str:
        if not self.is_configured():
            raise RuntimeError(f"Variable d'environnement manquante : {_ENV_KEY}")
        client = self._get_client()

        if supports_vision:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            contents = [image_part, prompt]
        else:
            logger.warning(
                "Modèle texte seul sélectionné pour une analyse image : %s. "
                "L'image ne sera pas transmise à l'API.",
                model_id,
            )
            contents = [prompt]

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=contents,
            )
        except Exception as exc:
            logger.error(
                "Appel API Google AI Studio échoué",
                extra={"model": model_id, "error": str(exc)},
            )
            raise RuntimeError(f"Erreur API Google AI Studio ({model_id}) : {exc}") from exc

        if not response.text:
            logger.warning("Réponse IA vide (filtres de sécurité ou modèle muet)", extra={"model": model_id})
        return response.text or ""
