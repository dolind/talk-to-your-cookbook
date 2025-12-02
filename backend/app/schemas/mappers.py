from app.models.ocr import BookScanORM, ImageORM
from app.schemas.ocr import (
    BookScanRead,
    PageScanRead,
    SegmentationSegment,
)


def image_row_to_dto(row: ImageORM) -> PageScanRead:
    return PageScanRead(
        id=row.id,
        filename=row.filename,
        bookScanID=row.book_scan_id,
        page_number=row.page_number,
        scanDate=row.scan_date,
        ocr_path=row.ocr_path,
        title=row.title,
        page_segments=[SegmentationSegment(**seg) for seg in row.recipe_areas] if row.recipe_areas else [],
        status=row.status,
        page_type=row.page_type,
    )


def book_row_to_dto(row: BookScanORM) -> BookScanRead:
    return BookScanRead(
        id=row.id,
        title=row.title,
        user_id=row.user_id,
    )
