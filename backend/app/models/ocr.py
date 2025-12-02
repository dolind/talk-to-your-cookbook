from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import flag_modified

from app.database.base import Base
from app.models.model_helper import generate_uuid
from app.models.recipe import Recipe
from app.schemas.ocr import PageStatus, PageType, RecordStatus

if TYPE_CHECKING:
    from app.models.user import User


class ClassificationRecordORM(Base):
    __tablename__ = "classification_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)

    book_scan_id: Mapped[str] = mapped_column(
        String, ForeignKey("book_scans.id", ondelete="CASCADE"), index=True, nullable=False
    )

    recipe_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("recipes.id", ondelete="SET NULL"), index=True, nullable=True
    )

    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.QUEUED, index=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    validation_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 👇 Pages used in this scan record — list of dicts like:
    # { image_id, all_blocks, block_indices?, page_number? }
    pages: Mapped[dict] = mapped_column(JSON, nullable=True)

    @hybrid_property
    def text_pages(self) -> list[dict]:
        return (self.pages or {}).get("text_pages", [])

    @hybrid_property
    def image_pages(self) -> list[dict]:
        return (self.pages or {}).get("image_pages", [])

    @text_pages.setter
    def text_pages(self, value: list[dict]):
        if self.pages is None:
            self.pages = {}
        self.pages["text_pages"] = value
        flag_modified(self, "pages")

    @image_pages.setter
    def image_pages(self, value: list[dict]):
        if self.pages is None:
            self.pages = {}
        self.pages["image_pages"] = value
        flag_modified(self, "pages")

    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    book_scan: Mapped["BookScanORM"] = relationship("BookScanORM", backref="scan_records")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")

    __table_args__ = (Index("ix_scan_records_book_status", "book_scan_id", "status"),)


class BookScanORM(Base):
    __tablename__ = "book_scans"

    id: Mapped[str] = Column(String, primary_key=True, default=generate_uuid)
    title: Mapped[str] = Column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Relationship: one book scan → many images
    images: Mapped[List["ImageORM"]] = relationship(
        "ImageORM",
        back_populates="book_scan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship("User", back_populates="book_scans")


class ImageORM(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    book_scan_id: Mapped[str] = mapped_column(
        String, ForeignKey("book_scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    scan_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())

    ocr_path: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    recipe_areas: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    page_type: Mapped[Optional[PageType]] = mapped_column(
        SAEnum(PageType, name="page_type_enum"),
        nullable=True,
    )
    book_scan: Mapped["BookScanORM"] = relationship("BookScanORM", back_populates="images")
    status: Mapped[PageStatus] = Column(Enum(PageStatus), default=PageStatus.QUEUED, index=True)
