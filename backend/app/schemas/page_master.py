"""
Schémas Pydantic pour le JSON maître de page — source canonique de toutes les sorties.
"""
# 1. stdlib
from datetime import datetime
from enum import Enum
from typing import Any, Literal

# 2. third-party
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegionType(str, Enum):
    TEXT_BLOCK = "text_block"
    MINIATURE = "miniature"
    DECORATED_INITIAL = "decorated_initial"
    MARGIN = "margin"
    RUBRIC = "rubric"
    OTHER = "other"


class Region(BaseModel):
    id: str
    type: RegionType
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    polygon: list[list[int]] | None = None
    parent_region_id: str | None = None

    @field_validator("bbox")
    @classmethod
    def bbox_must_be_valid(cls, v: list[int]) -> list[int]:
        if any(x < 0 for x in v):
            raise ValueError("bbox: toutes les valeurs doivent être >= 0")
        if v[2] <= 0 or v[3] <= 0:
            raise ValueError("bbox: width et height doivent être > 0")
        return v


class ImageInfo(BaseModel):
    """Métadonnées image — CLAUDE.md §4.2.

    Supporte deux modes :
    - IIIF natif : iiif_service_url renseigné, images streamées depuis le serveur
      d'origine (pas de stockage local). derivative_web / thumbnail = None.
    - Upload local : master = chemin local, derivative_web / thumbnail = chemins
      des dérivés sur disque (mode legacy ou upload de fichiers).
    """

    master: str                           # URL source (service IIIF ou statique) ou chemin local
    derivative_web: str | None = None     # chemin dérivé 1500px (legacy/upload)
    thumbnail: str | None = None          # chemin thumbnail 256px (legacy/upload)
    iiif_base: str | None = None          # compat arrière
    iiif_service_url: str | None = None   # URL du IIIF Image Service (zoom tuilé)
    manifest_url: str | None = None       # URL du manifest source (provenance)
    width: int                            # largeur du canvas original
    height: int                           # hauteur du canvas original


class OCRResult(BaseModel):
    diplomatic_text: str = ""
    blocks: list[dict] = []
    lines: list[dict] = []
    language: str = "la"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    uncertain_segments: list[str] = []


class Translation(BaseModel):
    fr: str = ""
    en: str = ""


class Summary(BaseModel):
    """Résumé — CLAUDE.md §4.2."""

    short: str = ""
    detailed: str = ""


class CommentaryClaim(BaseModel):
    claim: str
    evidence_region_ids: list[str] = []
    certainty: Literal["high", "medium", "low", "speculative"] = "medium"


class Commentary(BaseModel):
    public: str = ""
    scholarly: str = ""
    claims: list[CommentaryClaim] = []


class ProcessingInfo(BaseModel):
    provider: str
    model_id: str
    model_display_name: str
    prompt_version: str
    raw_response_path: str
    processed_at: datetime
    cost_estimate_usd: float | None = None


class EditorialStatus(str, Enum):
    MACHINE_DRAFT = "machine_draft"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    VALIDATED = "validated"
    PUBLISHED = "published"


class EditorialInfo(BaseModel):
    status: EditorialStatus = EditorialStatus.MACHINE_DRAFT
    validated: bool = False
    validated_by: str | None = None
    version: int = 1
    notes: list[str] = []


class PageMaster(BaseModel):
    schema_version: str = "1.0"
    page_id: str
    corpus_profile: str
    manuscript_id: str
    folio_label: str
    sequence: int

    image: ImageInfo
    layout: dict
    ocr: OCRResult | None = None
    translation: Translation | None = None
    summary: Summary | None = None
    commentary: Commentary | None = None
    extensions: dict[str, Any] = {}

    processing: ProcessingInfo | None = None
    editorial: EditorialInfo = Field(default_factory=EditorialInfo)
