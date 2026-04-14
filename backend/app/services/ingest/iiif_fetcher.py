"""
Téléchargement d'images depuis des URLs IIIF via httpx.

Inclut un rate-limiter global et un retry avec backoff exponentiel
pour respecter les limites des serveurs IIIF patrimoniaux (Gallica, etc.).
"""
# 1. stdlib
import logging
import re
import threading
import time

# 2. third-party
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0  # secondes (connect 15s + read 60s)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; IIIFStudio/1.0; "
        "+https://huggingface.co/spaces/Ma-Ri-Ba-Ku/iiif-studio)"
    ),
    "Accept": "image/jpeg,image/png,image/*,*/*",
}

# ── Rate-limiter global ────────────────────────────────────────────────────
# Gallica and similar IIIF servers enforce strict rate limits.
# We enforce a minimum delay between consecutive requests.
_MIN_REQUEST_INTERVAL = 1.0  # secondes entre deux requêtes
_rate_lock = threading.Lock()
_last_request_time = 0.0

# ── Retry configuration ───────────────────────────────────────────────────
_MAX_RETRIES = 4
_INITIAL_BACKOFF = 2.0  # secondes, doublé à chaque retry


def _wait_rate_limit() -> None:
    """Attend si nécessaire pour respecter le débit maximal vers les serveurs IIIF."""
    global _last_request_time
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


def _fetch_with_retry(url: str, timeout: float) -> httpx.Response:
    """GET avec retry et backoff exponentiel sur 429 / 5xx.

    Respecte le header Retry-After si présent dans la réponse 429.
    """
    backoff = _INITIAL_BACKOFF
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        _wait_rate_limit()
        try:
            response = httpx.get(
                url,
                headers=_HEADERS,
                follow_redirects=True,
                timeout=httpx.Timeout(timeout, connect=15.0),
            )
            if response.status_code == 429 or response.status_code >= 500:
                # Respect Retry-After header if present
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        wait_time = backoff
                else:
                    wait_time = backoff

                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "HTTP %d — retry %d/%d dans %.1fs",
                        response.status_code,
                        attempt + 1,
                        _MAX_RETRIES,
                        wait_time,
                        extra={"url": url},
                    )
                    time.sleep(wait_time)
                    backoff *= 2
                    continue
                # Last attempt: raise
                response.raise_for_status()

            response.raise_for_status()
            return response

        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Timeout — retry %d/%d dans %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    backoff,
                    extra={"url": url},
                )
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    # Should not reach here, but just in case
    raise last_exc or RuntimeError(f"Échec après {_MAX_RETRIES} retries : {url}")


def _rewrite_full_to_reduced(url: str, max_px: int = 1500) -> str:
    """Réécrit une URL IIIF /full/full/ ou /full/max/ en /full/!{max_px},{max_px}/.

    Cela demande au serveur IIIF de redimensionner côté serveur au lieu de
    retourner l'image en pleine résolution. Beaucoup plus rapide et respectueux
    des quotas serveur.

    Si l'URL n'est pas une URL IIIF standard, elle est retournée inchangée.
    """
    # Match IIIF Image API pattern: .../full/(full|max)/0/(default|native).(jpg|png|...)
    pattern = r"(/full/)(full|max)(/0/)"
    replacement = rf"\g<1>!{max_px},{max_px}\3"
    new_url = re.sub(pattern, replacement, url)
    if new_url != url:
        logger.info("URL IIIF réécrite: full → !%d,%d", max_px, max_px, extra={"original": url})
    return new_url


def fetch_iiif_image(url: str, timeout: float = _DEFAULT_TIMEOUT) -> bytes:
    """Télécharge une image depuis une URL IIIF complète.

    Si l'URL demande la pleine résolution (/full/full/ ou /full/max/),
    elle est automatiquement réécrite pour demander un dérivé 1500px max
    côté serveur, ce qui est plus rapide et évite le rate-limiting.

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
    url = _rewrite_full_to_reduced(url)
    logger.info("Fetching IIIF image", extra={"url": url})
    response = _fetch_with_retry(url, timeout)
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
    response = _fetch_with_retry(derivative_url, timeout)
    logger.info(
        "IIIF derivative fetched",
        extra={"url": derivative_url, "size_bytes": len(response.content)},
    )
    return response.content
