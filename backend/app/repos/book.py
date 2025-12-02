from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ocr import BookScanORM
from app.schemas.mappers import book_row_to_dto
from app.schemas.ocr import BookScanCreate, BookScanRead


class BookScanRepository:
    def __init__(self, session: AsyncSession):
        self.s = session

    # ──────────────────────────────────────────────────────────────
    async def save(self, bs: BookScanCreate, owner_id: str) -> BookScanRead:
        row = BookScanORM(
            title=bs.title,
            user_id=owner_id,
        )
        self.s.add(row)
        await self.s.flush()
        await self.s.refresh(row)
        await self.s.commit()
        return book_row_to_dto(row)

    async def get(self, book_scan_id: str, owner_id: str) -> Optional[BookScanRead]:
        stmt = select(BookScanORM).where(BookScanORM.id == book_scan_id, BookScanORM.user_id == owner_id)
        row = (await self.s.execute(stmt)).scalar_one_or_none()
        return book_row_to_dto(row) if row else None

    async def get_owned(self, book_scan_id: str, owner_id: str) -> Optional[BookScanRead]:
        """Alias maintained for backwards compatibility."""
        return await self.get(book_scan_id, owner_id)

    async def list_all(self, owner_id: str) -> List[BookScanRead]:
        stmt = (
            select(BookScanORM)
            .where(BookScanORM.title != "", BookScanORM.user_id == owner_id)
            .order_by(BookScanORM.title)
        )
        rows = (await self.s.execute(stmt)).scalars().all()
        return [book_row_to_dto(r) for r in rows]

    async def delete_if_unlinked(self, book_scan_id: str, owner_id: str) -> bool:
        stmt = (
            select(BookScanORM)
            .where(BookScanORM.id == book_scan_id, BookScanORM.user_id == owner_id)
            .options(selectinload(BookScanORM.images))  # ⬅ Eager load related images
        )
        result = await self.s.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False

        # Check if it has any linked entities; adapt as per your actual model
        has_connections = bool(row.images)
        if has_connections:
            return False

        await self.s.delete(row)
        await self.s.flush()
        await self.s.commit()
        return True
