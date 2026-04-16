"""
Modèle SQLAlchemy pour l'index de recherche plein texte (FTS5).

La table page_search_fts est une table virtuelle FTS5 créée via SQL brut.
Ce modèle représente les données indexées pour chaque page analysée.
"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class PageSearchIndex(Base):
    """Index de recherche — table miroir pour les données indexables."""

    __tablename__ = "page_search"

    page_id: Mapped[str] = mapped_column(String, primary_key=True)
    corpus_profile: Mapped[str] = mapped_column(String, nullable=False, default="")
    manuscript_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    folio_label: Mapped[str] = mapped_column(String, nullable=False, default="")
    diplomatic_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    translation_fr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Pre-normalized concatenation of all text fields for SQL LIKE search
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
