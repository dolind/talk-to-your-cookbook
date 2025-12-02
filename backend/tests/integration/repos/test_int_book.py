import datetime

import pytest

from app.models.ocr import BookScanORM, ImageORM
from app.models.user import User
from app.repos.book import BookScanRepository
from app.schemas.ocr import BookScanCreate


@pytest.mark.asyncio
async def test_create_book_scan(db_session, test_user: User):
    book_scan = BookScanORM(title="Test Book", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.commit()

    result = await db_session.get(BookScanORM, book_scan.id)
    assert result is not None
    assert result.title == "Test Book"
    assert result.user_id == test_user.id


@pytest.mark.asyncio
async def test_save_book_scan(db_session, test_user: User):
    repo = BookScanRepository(db_session)

    # Act
    created = await repo.save(BookScanCreate(title="My Book"), test_user.id)

    # Assert
    assert created.id is not None
    assert created.title == "My Book"


@pytest.mark.asyncio
async def test_get_book_scan(db_session, test_user: User):
    book = BookScanORM(title="Get Me", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    repo = BookScanRepository(db_session)

    result = await repo.get(book.id, test_user.id)

    assert result is not None
    assert result.id == book.id
    assert result.title == "Get Me"


@pytest.mark.asyncio
async def test_get_book_scan_not_found(db_session, test_user: User):
    repo = BookScanRepository(db_session)

    result = await repo.get("non-existent-id", test_user.id)

    assert result is None


@pytest.mark.asyncio
async def test_list_all_book_scans(db_session, test_user: User):
    db_session.add_all(
        [
            BookScanORM(title="Zeta Book", user_id=test_user.id),
            BookScanORM(title="Alpha Book", user_id=test_user.id),
            BookScanORM(title="", user_id=test_user.id),  # Should be excluded
        ]
    )
    await db_session.flush()

    repo = BookScanRepository(db_session)
    results = await repo.list_all(test_user.id)

    titles = [b.title for b in results]
    assert "Alpha Book" in titles
    assert "Zeta Book" in titles
    assert "" not in titles
    assert titles == sorted(titles)  # Ordered by title


@pytest.mark.asyncio
async def test_delete_unlinked_book_scan(db_session, test_user: User):
    book = BookScanORM(title="Unlinked", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    repo = BookScanRepository(db_session)
    deleted = await repo.delete_if_unlinked(book.id, test_user.id)

    assert deleted is True
    assert await db_session.get(BookScanORM, book.id) is None


@pytest.mark.asyncio
async def test_delete_book_scan_with_pages_fails(db_session, test_user: User):
    book = BookScanORM(title="Linked", user_id=test_user.id)
    image = ImageORM(filename="page.jpg", book_scan=book, scan_date=datetime.datetime.now())
    db_session.add_all([book, image])
    await db_session.flush()

    repo = BookScanRepository(db_session)
    deleted = await repo.delete_if_unlinked(book.id, test_user.id)

    assert deleted is False
    assert await db_session.get(BookScanORM, book.id) is not None


@pytest.mark.asyncio
async def test_delete_book_scan_not_found(db_session, test_user: User):
    repo = BookScanRepository(db_session)
    result = await repo.delete_if_unlinked("non-existent-id", test_user.id)

    assert result is False
