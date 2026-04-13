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


def fetch_iiif_derivative(
    service_url: str,
    max_px: int = 1500,
    timeout: float = _DEFAULT_TIMEOUT,
) -> bytes:
    """Télécharge un dérivé via l'IIIF Image API — jamais stocké sur disque.

    Construit l'URL : {service_url}/full/!{max_px},{max_px}/0/default.jpg
    Le serveur IIIF retourne une image redimensionnée côté serveur.

    Args:
        service_url: URL du IIIF Image Service (sans le suffix /full/.../default.jpg).
        max_px: taille max du grand côté (défaut : 1500).
        timeout: délai maximal en secondes.

    Returns:
        Contenu brut de l'image JPEG en bytes.
    """
    # Pattern IIIF Image API : !w,h = "best fit" (le serveur choisit)
    derivative_url = f"{service_url.rstrip('/')}/full/!{max_px},{max_px}/0/default.jpg"
    logger.info("Fetching IIIF derivative", extra={"url": derivative_url, "max_px": max_px})
    response = httpx.get(
        derivative_url,
        headers=_HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(timeout, connect=10.0),
    )
    response.raise_for_status()
    logger.info(
        "IIIF derivative fetched",
        extra={"url": derivative_url, "size_bytes": len(response.content)},
    )
    return response.content
