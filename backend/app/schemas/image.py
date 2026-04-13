"""
Schémas Pydantic pour les métadonnées image du pipeline.

Deux schémas coexistent :
- ImageDerivativeInfo : dérivés stockés sur disque (upload de fichiers)
- ImageSourceInfo     : source IIIF sans stockage local (mode natif)
"""
# 2. third-party
from pydantic import BaseModel


class ImageDerivativeInfo(BaseModel):
    """Résultat de la normalisation d'une image : dimensions originales et chemins des dérivés.

    Utilisé pour les images uploadées via /ingest/files (stockage local).
    """

    original_url: str
    original_width: int
    original_height: int
    derivative_path: str
    derivative_width: int
    derivative_height: int
    thumbnail_path: str
    thumbnail_width: int
    thumbnail_height: int


class ImageSourceInfo(BaseModel):
    """Source d'image IIIF — pas de stockage local.

    Utilisé pour les images ingérées via manifest ou URLs IIIF.
    Les bytes ne sont jamais écrits sur disque : téléchargés en RAM
    pour l'IA, puis jetés.
    """

    original_url: str                     # URL statique de l'image (fallback)
    iiif_service_url: str | None = None   # URL du service IIIF Image API
    manifest_url: str | None = None       # URL du manifest source
    is_iiif: bool = False                 # a un IIIF Image Service détecté ?
    original_width: int
    original_height: int
