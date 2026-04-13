"""
Tests de détection du IIIF Image Service à l'ingestion.

Vérifie :
- Extraction depuis un canvas IIIF 3.0 avec ImageService3
- Extraction depuis un canvas IIIF 2.x avec service @id
- Détection par pattern URL (Gallica, etc.)
- Fallback quand aucun service n'est trouvé
- Détection depuis URL directe (ingest/iiif-images)
"""
import pytest

from app.api.v1.ingest import (
    _detect_iiif_service_from_url,
    _extract_iiif_service,
)


# ---------------------------------------------------------------------------
# _extract_iiif_service — IIIF 3.0
# ---------------------------------------------------------------------------

def test_extract_iiif3_with_image_service3():
    """Canvas IIIF 3.0 avec service ImageService3 explicite."""
    canvas = {
        "width": 3543,
        "height": 4724,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29/full/max/0/default.jpg",
                    "type": "Image",
                    "service": [{
                        "id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29",
                        "type": "ImageService3",
                        "profile": "level2",
                    }],
                },
            }],
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29"
    assert w == 3543
    assert h == 4724


def test_extract_iiif3_with_image_service2():
    """Canvas IIIF 3.0 avec un service de type ImageService2."""
    canvas = {
        "width": 2000,
        "height": 3000,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://example.com/image/1/full/max/0/default.jpg",
                    "type": "Image",
                    "service": [{
                        "id": "https://example.com/image/1",
                        "type": "ImageService2",
                        "profile": "level1",
                    }],
                },
            }],
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url == "https://example.com/image/1"
    assert w == 2000


def test_extract_iiif3_service_as_dict():
    """Le champ service peut être un dict au lieu d'une liste."""
    canvas = {
        "width": 1000,
        "height": 1500,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://example.com/img/full/max/0/default.jpg",
                    "service": {
                        "id": "https://example.com/img",
                        "type": "ImageService3",
                    },
                },
            }],
        }],
    }
    svc_url, _, _ = _extract_iiif_service(canvas)
    assert svc_url == "https://example.com/img"


def test_extract_iiif3_fallback_url_pattern():
    """Sans service explicite, détecte le pattern Image API dans body.id."""
    canvas = {
        "width": 3000,
        "height": 4000,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29/full/max/0/default.jpg",
                    "type": "Image",
                    # Pas de "service" !
                },
            }],
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29"
    assert w == 3000


def test_extract_iiif3_no_service_no_pattern():
    """Canvas sans service et sans pattern Image API → None."""
    canvas = {
        "width": 800,
        "height": 600,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://example.com/static/page1.jpg",
                    "type": "Image",
                },
            }],
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url is None
    assert w == 800
    assert h == 600


# ---------------------------------------------------------------------------
# _extract_iiif_service — IIIF 2.x
# ---------------------------------------------------------------------------

def test_extract_iiif2_with_service():
    """Canvas IIIF 2.x avec service dans resource."""
    canvas = {
        "width": 4000,
        "height": 5000,
        "images": [{
            "resource": {
                "@id": "https://example.com/image/2/full/full/0/default.jpg",
                "service": {
                    "@id": "https://example.com/image/2",
                    "@type": "ImageService2",
                },
            },
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url == "https://example.com/image/2"
    assert w == 4000


def test_extract_iiif2_fallback_url_pattern():
    """IIIF 2.x : détection par pattern dans resource @id."""
    canvas = {
        "width": 2500,
        "height": 3500,
        "images": [{
            "resource": {
                "@id": "https://iiif.bodleian.ox.ac.uk/image/abc123/full/full/0/default.jpg",
            },
        }],
    }
    svc_url, _, _ = _extract_iiif_service(canvas)
    assert svc_url == "https://iiif.bodleian.ox.ac.uk/image/abc123"


def test_extract_iiif2_no_service():
    """IIIF 2.x sans service et URL statique → None."""
    canvas = {
        "width": 1200,
        "height": 1600,
        "images": [{
            "resource": {
                "@id": "https://example.com/images/scan.png",
            },
        }],
    }
    svc_url, w, h = _extract_iiif_service(canvas)
    assert svc_url is None
    assert w == 1200


# ---------------------------------------------------------------------------
# _extract_iiif_service — cas limites
# ---------------------------------------------------------------------------

def test_extract_empty_canvas():
    """Canvas vide → None sans crash."""
    svc_url, w, h = _extract_iiif_service({})
    assert svc_url is None
    assert w is None
    assert h is None


def test_extract_service_url_trailing_slash_stripped():
    """L'URL du service ne doit pas se terminer par /."""
    canvas = {
        "width": 1000,
        "height": 1000,
        "items": [{
            "items": [{
                "body": {
                    "id": "https://example.com/img/full/max/0/default.jpg",
                    "service": [{
                        "id": "https://example.com/img/",
                        "type": "ImageService3",
                    }],
                },
            }],
        }],
    }
    svc_url, _, _ = _extract_iiif_service(canvas)
    assert svc_url == "https://example.com/img"
    assert not svc_url.endswith("/")


# ---------------------------------------------------------------------------
# _detect_iiif_service_from_url — détection depuis URL directe
# ---------------------------------------------------------------------------

def test_detect_from_gallica_url():
    """URL Gallica complète → service URL déduit."""
    url = "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29/full/max/0/default.jpg"
    assert _detect_iiif_service_from_url(url) == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8432314s/f29"


def test_detect_from_iiif_url_with_size():
    """URL avec taille spécifique → service URL déduit."""
    url = "https://example.com/iiif/img1/full/!1500,1500/0/default.jpg"
    assert _detect_iiif_service_from_url(url) == "https://example.com/iiif/img1"


def test_detect_from_static_url_returns_none():
    """URL statique (pas de pattern IIIF) → None."""
    url = "https://example.com/images/page1.jpg"
    assert _detect_iiif_service_from_url(url) is None


def test_detect_from_iiif_url_different_format():
    """URL avec format PNG au lieu de JPEG."""
    url = "https://example.com/iiif/img2/full/max/0/default.png"
    assert _detect_iiif_service_from_url(url) == "https://example.com/iiif/img2"
