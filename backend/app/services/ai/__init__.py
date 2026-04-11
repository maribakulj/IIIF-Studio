"""
Services AI — providers Google AI, registre de modèles, et analyse IA.

Les imports de providers sont différés (lazy) pour éviter de charger les SDK
tiers (google-genai, mistralai) au démarrage. Cela permet à l'application
de fonctionner même si un SDK n'est pas installé.
"""


def __getattr__(name: str):
    """Import paresseux — les symboles sont résolus au premier accès."""
    _lazy_map = {
        "run_primary_analysis": "app.services.ai.analyzer",
        "build_client": "app.services.ai.client_factory",
        "build_model_config": "app.services.ai.model_registry",
        "list_all_models": "app.services.ai.model_registry",
        "load_and_render_prompt": "app.services.ai.prompt_loader",
        "parse_ai_response": "app.services.ai.response_parser",
        "ParseError": "app.services.ai.response_parser",
    }
    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "list_all_models",
    "build_model_config",
    "build_client",
    "load_and_render_prompt",
    "parse_ai_response",
    "ParseError",
    "run_primary_analysis",
]
