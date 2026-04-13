"""
Téléchargement d'images depuis des URLs IIIF via httpx.
"""
# 1. stdlib
import logging

# 2. third-party
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0  # secondes (connect 10s + read 30s)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; IIIFStudio/1.0; "
        "+https://huggingface.co/spaces/Ma-Ri-Ba-Ku/iiif-studio)"
    ),
    "Accept": "image/jpeg,image/png,image/*,*/*",
}


def fetch_iiif_image(url: str, timeout: float = _DEFAULT_TIMEOUT) -> bytes:
    """Télécharge une image depuis une URL IIIF complète.

    Args:
        url: URL complète de l'image (ex. https://.../full/max/0/default.jpg).
        timeout: délai maximal en secondes (défaut : 60 s).

    Returns:
        Contenu brut de l'image en bytes.

    Raises:
        httpx.HTTPStatusError: si le serveur retourne un code 4xx ou 5xx.
        httpx.TimeoutException: si la requête dépasse le délai.
        httpx.RequestError: pour toute autre erreur réseau.
    """
    logger.info("Fetching IIIF image", extra={"url": url})
    response = httpx.get(
        url,
        headers=_HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(timeout, connect=10.0),
    )
    response.raise_for_status()
    logger.info(
        "IIIF image fetched",
        extra={"url": url, "size_bytes": len(response.content)},
    )
    return response.content
