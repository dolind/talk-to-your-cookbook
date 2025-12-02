from datetime import datetime

import pytest
from sqlalchemy.exc import NoResultFound

from app.models.ocr import BookScanORM, ImageORM
from app.repos.image_repo import ImageRepository
from app.schemas.ocr import PageScanCreate, PageScanUpdate, PageType


@pytest.mark.asyncio
async def test_save_image(db_session, test_user):
    # Arrange: Create a BookScan as the image needs a foreign key
    book_scan = BookScanORM(title="My Scan", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.flush()  # to get book_scan.id

    repo = ImageRepository(db_session)

    # Create input DTO
    image_in = PageScanCreate(
        filename="page1.jpg",
        bookScanID=book_scan.id,
    )

    # Act
    saved = await repo.save(image_in, test_user.id)

    # Assert
    assert saved.id is not None
    assert saved.filename == "page1.jpg"
    assert saved.bookScanID == book_scan.id


@pytest.mark.asyncio
async def test_get_image(db_session, test_user):
    # Setup
    book_scan = BookScanORM(title="Scan for get", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.flush()

    image = ImageORM(
        filename="existing.jpg",
        book_scan_id=book_scan.id,
        page_number=5,
        scan_date=datetime.now(),
    )
    db_session.add(image)
    await db_session.flush()

    repo = ImageRepository(db_session)

    # Act
    result = await repo.get(image.id)

    # Assert
    assert result is not None
    assert result.id == image.id
    assert result.filename == image.filename


@pytest.mark.asyncio
async def test_list_by_book(db_session, test_user):
    # Setup
    book_scan = BookScanORM(title="Scan for list", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.flush()

    images = [
        ImageORM(filename="1.jpg", book_scan_id=book_scan.id, page_number=1),
        ImageORM(filename="2.jpg", book_scan_id=book_scan.id, page_number=2),
    ]
    db_session.add_all(images)
    await db_session.flush()

    repo = ImageRepository(db_session)

    # Act
    results = await repo.list_by_book(book_scan.id, test_user.id)

    # Assert
    assert len(results) == 2
    assert results[0].filename == "1.jpg"
    assert results[1].filename == "2.jpg"


@pytest.mark.asyncio
async def test_delete_image(db_session, test_user):
    # Setup
    book_scan = BookScanORM(title="Scan for delete", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.flush()

    image = ImageORM(filename="to_delete.jpg", book_scan_id=book_scan.id, scan_date=datetime.now())
    db_session.add(image)
    await db_session.flush()

    repo = ImageRepository(db_session)

    # Act
    await repo.delete(image.id, test_user.id)

    # Assert
    result = await db_session.get(ImageORM, image.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_image_not_found(db_session, test_user):
    repo = ImageRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.delete("non-existent-id", test_user.id)


@pytest.mark.asyncio
async def test_update_image(db_session, test_user):
    # Setup
    book_scan = BookScanORM(title="Scan for update", user_id=test_user.id)
    db_session.add(book_scan)
    await db_session.flush()

    image = ImageORM(
        filename="original.jpg",
        book_scan_id=book_scan.id,
        page_number=1,
        scan_date=datetime.now(),
        title="Original Title",
        page_type=PageType.TEXT,
    )
    db_session.add(image)
    await db_session.flush()

    repo = ImageRepository(db_session)

    update_data = PageScanUpdate(id=image.id, filename="updated.jpg", title="Updated Title")

    # Act
    updated = await repo.update(update_data, test_user.id)

    # Assert
    assert updated.id == image.id
    assert updated.filename == "updated.jpg"
    assert updated.title == "Updated Title"


@pytest.mark.asyncio
async def test_update_image_not_found(db_session, test_user):
    repo = ImageRepository(db_session)

    update_data = PageScanUpdate(id="non-existent-id", filename="nope.jpg")

    with pytest.raises(NoResultFound):
        await repo.update(update_data, test_user.id)


@pytest.mark.asyncio
async def test_save_rejects_wrong_owner(db_session, test_user, user_factory):
    other = await user_factory()
    foreign_book = BookScanORM(title="Not yours", user_id=other.id)
    db_session.add(foreign_book)
    await db_session.flush()

    repo = ImageRepository(db_session)
    img = PageScanCreate(filename="x.jpg", bookScanID=foreign_book.id)

    with pytest.raises(NoResultFound):
        await repo.save(img, owner_id=test_user.id)


@pytest.mark.asyncio
async def test_save_assigns_incremental_page_number(db_session, test_user):
    book = BookScanORM(title="Scan", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    img1 = ImageORM(filename="1.jpg", book_scan_id=book.id, page_number=1)
    img2 = ImageORM(filename="2.jpg", book_scan_id=book.id, page_number=2)
    db_session.add_all([img1, img2])
    await db_session.flush()

    repo = ImageRepository(db_session)

    created = await repo.save(PageScanCreate(filename="next.jpg", bookScanID=book.id), test_user.id)

    assert created.page_number == 3


@pytest.mark.asyncio
async def test_get_owned_filters_out_foreign(db_session, test_user, user_factory):
    other = await user_factory()

    book = BookScanORM(title="Scan", user_id=other.id)
    db_session.add(book)
    await db_session.flush()

    img = ImageORM(filename="x.jpg", book_scan_id=book.id, page_number=1)
    db_session.add(img)
    await db_session.flush()

    repo = ImageRepository(db_session)

    result = await repo.get_owned(img.id, owner_id=test_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_list_by_book_filters_non_owner(db_session, test_user, user_factory):
    other = await user_factory()

    book = BookScanORM(title="Scan", user_id=other.id)
    db_session.add(book)
    await db_session.flush()

    img = ImageORM(filename="x.jpg", book_scan_id=book.id, page_number=1)
    db_session.add(img)
    await db_session.flush()

    repo = ImageRepository(db_session)

    results = await repo.list_by_book(book.id, owner_id=test_user.id)
    assert results == []


@pytest.mark.asyncio
async def test_update_page_number_not_found(db_session):
    repo = ImageRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.update_page_number("missing", 10)


@pytest.mark.asyncio
async def test_update_page_number_rejects_conflict(db_session, test_user):
    book = BookScanORM(title="Scan", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    img1 = ImageORM(filename="1.jpg", book_scan_id=book.id, page_number=1)
    img2 = ImageORM(filename="2.jpg", book_scan_id=book.id, page_number=2)
    db_session.add_all([img1, img2])
    await db_session.flush()

    repo = ImageRepository(db_session)

    with pytest.raises(ValueError):
        await repo.update_page_number(img1.id, target_number=2)


@pytest.mark.asyncio
async def test_update_rejects_move_to_foreign_book(db_session, test_user, user_factory):
    owner = test_user
    other = await user_factory()

    book1 = BookScanORM(title="Scan1", user_id=owner.id)
    book2 = BookScanORM(title="Scan2", user_id=other.id)
    db_session.add_all([book1, book2])
    await db_session.flush()

    img = ImageORM(filename="x.jpg", book_scan_id=book1.id, page_number=1)
    db_session.add(img)
    await db_session.flush()

    repo = ImageRepository(db_session)

    update_dto = PageScanUpdate(id=img.id, bookScanID=book2.id)

    with pytest.raises(NoResultFound):  # forbidden
        await repo.update(update_dto, owner_id=owner.id)


@pytest.mark.asyncio
async def test_update_multiple_fields(db_session, test_user):
    book = BookScanORM(title="Scan", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    img = ImageORM(filename="orig.jpg", book_scan_id=book.id, page_number=1)
    db_session.add(img)
    await db_session.flush()

    repo = ImageRepository(db_session)

    upd = PageScanUpdate(id=img.id, filename="new.jpg", page_number=5, ocr_path="/ocr/test", title="Updated Title")

    out = await repo.update(upd, owner_id=test_user.id)

    assert out.filename == "new.jpg"
    assert out.page_number == 5
    assert out.ocr_path == "/ocr/test"
    assert out.title == "Updated Title"
