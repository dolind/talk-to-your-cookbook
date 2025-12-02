from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr import BookScanORM, ClassificationRecordORM
from app.schemas.ocr import (
    ClassificationRecordCreate,
    ClassificationRecordRead,
    ClassificationRecordUpdate,
)


def _select_record(record_id: str, owner_id: Optional[str] = None):
    stmt = select(ClassificationRecordORM).where(ClassificationRecordORM.id == record_id)
    if owner_id is not None:
        stmt = stmt.join(BookScanORM).where(BookScanORM.user_id == owner_id)
    return stmt


class ClassificationRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _ensure_book_owned(self, book_id: str, owner_id: Optional[str]):
        if owner_id is None:
            return
        stmt = select(BookScanORM.id).where(BookScanORM.id == book_id, BookScanORM.user_id == owner_id)
        if (await self.session.execute(stmt)).scalar_one_or_none() is None:
            raise NoResultFound(f"Book scan with id {book_id} not found for owner")

    async def get_by_id(self, record_id: str, owner_id: Optional[str] = None) -> ClassificationRecordRead:
        stmt = _select_record(record_id, owner_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise NoResultFound(f"ClassificationRecord with id {record_id} not found")

        return ClassificationRecordRead.model_validate(record)

    async def get_owned_by_id(self, record_id: str, owner_id: str) -> ClassificationRecordRead:
        stmt = (
            select(ClassificationRecordORM)
            .join(BookScanORM, ClassificationRecordORM.book_scan_id == BookScanORM.id)
            .where(ClassificationRecordORM.id == record_id, BookScanORM.user_id == owner_id)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise NoResultFound(f"ClassificationRecord with id {record_id} not found")

        return ClassificationRecordRead.model_validate(record)

    async def get_all_by_book_id(self, book_id: str, owner_id: Optional[str] = None) -> List[ClassificationRecordRead]:
        if owner_id is not None:
            await self._ensure_book_owned(book_id, owner_id)
        stmt = select(ClassificationRecordORM).where(ClassificationRecordORM.book_scan_id == book_id)
        if owner_id is not None:
            stmt = stmt.join(BookScanORM).where(BookScanORM.user_id == owner_id)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [ClassificationRecordRead.model_validate(r) for r in records]

    async def get_all_owned_by_book_id(self, book_id: str, owner_id: str) -> List[ClassificationRecordRead]:
        stmt = (
            select(ClassificationRecordORM)
            .join(BookScanORM, ClassificationRecordORM.book_scan_id == BookScanORM.id)
            .where(ClassificationRecordORM.book_scan_id == book_id, BookScanORM.user_id == owner_id)
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [ClassificationRecordRead.model_validate(r) for r in records]

    async def save(
        self, record: ClassificationRecordCreate, owner_id: Optional[str] = None
    ) -> ClassificationRecordRead:
        await self._ensure_book_owned(record.book_scan_id, owner_id)
        orm_obj = ClassificationRecordORM(book_scan_id=record.book_scan_id)
        self.session.add(orm_obj)

        await self.session.flush()

        await self.session.commit()

        # re-load for safety
        fresh = await self.session.get(ClassificationRecordORM, orm_obj.id)
        return ClassificationRecordRead.model_validate(fresh, from_attributes=True)

    async def update(
        self, record: ClassificationRecordUpdate, owner_id: Optional[str] = None
    ) -> ClassificationRecordRead:
        if record.id is None:
            raise ValueError("update() called without an id")
        # record.id must be present in the update payload

        stmt = _select_record(record.id, owner_id)
        result = await self.session.execute(stmt)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise NoResultFound(f"ClassificationRecord with id {record.id} not found")

        update_data = record.model_dump(exclude_unset=True)

        # Convert nested models (if any) before assigning
        if "validation_result" in update_data and update_data["validation_result"] is not None:
            update_data["validation_result"] = update_data["validation_result"]
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await self.session.commit()
        await self.session.refresh(db_obj)
        return ClassificationRecordRead.model_validate(db_obj)

    async def delete(self, record_id: str, owner_id: Optional[str] = None) -> None:
        stmt = _select_record(record_id, owner_id)
        result = await self.session.execute(stmt)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise NoResultFound(f"ClassificationRecord with id {record_id} not found")

        await self.session.delete(db_obj)
        await self.session.commit()

    async def delete_by_book_id(self, book_id: str, owner_id: Optional[str] = None) -> None:
        await self._ensure_book_owned(book_id, owner_id)
        stmt = delete(ClassificationRecordORM).where(ClassificationRecordORM.book_scan_id == book_id)
        if owner_id is not None:
            stmt = stmt.where(
                ClassificationRecordORM.book_scan_id.in_(
                    select(BookScanORM.id).where(BookScanORM.id == book_id, BookScanORM.user_id == owner_id)
                )
            )
        await self.session.execute(stmt)
        await self.session.commit()
