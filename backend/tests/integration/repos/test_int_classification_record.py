import pytest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.models.ocr import BookScanORM, ClassificationRecordORM
from app.repos.classification_record import ClassificationRecordRepository
from app.schemas.ocr import (
    ClassificationRecordCreate,
    ClassificationRecordUpdate,
    RecordStatus,
)

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------


async def _make_book(db_session, user_id, title="Scan"):
    book = BookScanORM(title=title, user_id=user_id)
    db_session.add(book)
    await db_session.flush()  # ensures book.id is available
    return book


async def _make_record(db_session, book_id, **kwargs):
    rec = ClassificationRecordORM(book_scan_id=book_id, **kwargs)
    db_session.add(rec)
    await db_session.commit()
    return rec


# -----------------------------------------------------------
# Existing Tests (fixed flush)
# -----------------------------------------------------------


@pytest.mark.asyncio
async def test_save_classification_record(db_session, test_user):
    book_scan = await _make_book(db_session, test_user.id, "Scan A")
    repo = ClassificationRecordRepository(db_session)

    record_in = ClassificationRecordCreate(book_scan_id=book_scan.id)
    saved = await repo.save(record_in, owner_id=test_user.id)

    assert saved.id is not None
    assert saved.book_scan_id == book_scan.id


@pytest.mark.asyncio
async def test_save_classification_record_rejects_foreign_owner(db_session, test_user, user_factory):
    other_user = await user_factory()
    foreign_book = await _make_book(db_session, other_user.id, "Not yours")

    repo = ClassificationRecordRepository(db_session)
    record_in = ClassificationRecordCreate(book_scan_id=foreign_book.id)

    with pytest.raises(NoResultFound):
        await repo.save(record_in, owner_id=test_user.id)


@pytest.mark.asyncio
async def test_get_classification_record_by_id(db_session, test_user):
    book = await _make_book(db_session, test_user.id, "Scan B")
    record = await _make_record(
        db_session,
        book.id,
        title="From DB",
        status=RecordStatus.NEEDS_REVIEW,
        approved=False,
    )

    repo = ClassificationRecordRepository(db_session)
    found = await repo.get_by_id(record.id)

    assert found.id == record.id
    assert found.title == "From DB"


@pytest.mark.asyncio
async def test_update_classification_record(db_session, test_user):
    book = await _make_book(db_session, test_user.id, "Scan C")
    record = await _make_record(
        db_session,
        book.id,
        title="Before",
        status=RecordStatus.QUEUED,
        approved=False,
        pages={},
    )

    repo = ClassificationRecordRepository(db_session)
    dto = ClassificationRecordUpdate(
        id=record.id,
        title="After",
        approved=True,
        status=RecordStatus.APPROVED,
    )

    updated = await repo.update(dto, owner_id=test_user.id)
    assert updated.id == record.id
    assert updated.title == "After"
    assert updated.status == RecordStatus.APPROVED
    assert updated.approved is True


@pytest.mark.asyncio
async def test_delete_classification_record(db_session, test_user):
    book = await _make_book(db_session, test_user.id, "Scan D")
    record = await _make_record(
        db_session,
        book.id,
        title="Delete Me",
        status=RecordStatus.APPROVED,
        pages=[],
    )

    repo = ClassificationRecordRepository(db_session)
    await repo.delete(record.id, owner_id=test_user.id)

    remaining = await db_session.get(ClassificationRecordORM, record.id)
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_by_book_id(db_session, test_user):
    book = await _make_book(db_session, test_user.id, "Scan E")
    await _make_record(
        db_session,
        book.id,
        title="To Delete",
        status=RecordStatus.APPROVED,
        pages=[],
    )

    repo = ClassificationRecordRepository(db_session)
    await repo.delete_by_book_id(book.id, owner_id=test_user.id)

    stmt = select(ClassificationRecordORM).where(ClassificationRecordORM.book_scan_id == book.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_update_classification_record_rejects_wrong_owner(db_session, test_user, user_factory):
    other_user = await user_factory()
    book = await _make_book(db_session, other_user.id, "Scan F")
    record = await _make_record(
        db_session,
        book.id,
        title="Foreign",
        status=RecordStatus.QUEUED,
    )

    repo = ClassificationRecordRepository(db_session)
    dto = ClassificationRecordUpdate(id=record.id, title="After")

    with pytest.raises(NoResultFound):
        await repo.update(dto, owner_id=test_user.id)

    refreshed = await db_session.get(ClassificationRecordORM, record.id)
    assert refreshed.title == "Foreign"


@pytest.mark.asyncio
async def test_delete_classification_record_rejects_wrong_owner(db_session, test_user, user_factory):
    other_user = await user_factory()
    book = await _make_book(db_session, other_user.id, "Scan G")
    record = await _make_record(
        db_session,
        book.id,
        title="Foreign",
        status=RecordStatus.QUEUED,
    )

    repo = ClassificationRecordRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.delete(record.id, owner_id=test_user.id)

    assert await db_session.get(ClassificationRecordORM, record.id) is not None


# -----------------------------------------------------------
# New Missing Coverage Tests
# -----------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_owner_filter_success(db_session, test_user):
    book = await _make_book(db_session, test_user.id, "OwnerBook")
    record = await _make_record(db_session, book.id)

    repo = ClassificationRecordRepository(db_session)
    out = await repo.get_by_id(record.id, owner_id=test_user.id)

    assert out.id == record.id
    assert out.book_scan_id == book.id


@pytest.mark.asyncio
async def test_get_by_id_owner_filter_rejects_foreign(db_session, test_user, user_factory):
    owner = await user_factory()
    book = await _make_book(db_session, owner.id)
    record = await _make_record(db_session, book.id)

    repo = ClassificationRecordRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.get_by_id(record.id, owner_id=test_user.id)


@pytest.mark.asyncio
async def test_get_owned_by_id_success(db_session, test_user):
    book = await _make_book(db_session, test_user.id)
    record = await _make_record(db_session, book.id)

    repo = ClassificationRecordRepository(db_session)
    out = await repo.get_owned_by_id(record.id, test_user.id)

    assert out.id == record.id


@pytest.mark.asyncio
async def test_get_owned_by_id_rejects_foreign(db_session, test_user, user_factory):
    other = await user_factory()
    book = await _make_book(db_session, other.id)
    record = await _make_record(db_session, book.id)

    repo = ClassificationRecordRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.get_owned_by_id(record.id, test_user.id)


@pytest.mark.asyncio
async def test_get_all_by_book_id_no_owner(db_session, test_user):
    book = await _make_book(db_session, test_user.id)
    rec1 = await _make_record(db_session, book.id)
    rec2 = await _make_record(db_session, book.id)

    repo = ClassificationRecordRepository(db_session)
    out = await repo.get_all_by_book_id(book.id)

    assert {r.id for r in out} == {rec1.id, rec2.id}


@pytest.mark.asyncio
async def test_get_all_by_book_id_owner_filter(db_session, test_user, user_factory):
    owner = test_user
    foreign = await user_factory()

    book_good = await _make_book(db_session, owner.id)
    book_bad = await _make_book(db_session, foreign.id)

    rec_good = await _make_record(db_session, book_good.id)
    await _make_record(db_session, book_bad.id)

    repo = ClassificationRecordRepository(db_session)

    out = await repo.get_all_by_book_id(book_good.id, owner.id)
    assert [r.id for r in out] == [rec_good.id]


@pytest.mark.asyncio
async def test_get_all_by_book_id_owner_rejects_foreign(db_session, test_user, user_factory):
    other = await user_factory()
    book = await _make_book(db_session, other.id)

    repo = ClassificationRecordRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.get_all_by_book_id(book.id, owner_id=test_user.id)


@pytest.mark.asyncio
async def test_update_missing_id_raises(db_session, test_user):
    repo = ClassificationRecordRepository(db_session)
    with pytest.raises(ValueError):
        await repo.update(ClassificationRecordUpdate(), owner_id=test_user.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(db_session, test_user):
    repo = ClassificationRecordRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.delete("nope", owner_id=test_user.id)


@pytest.mark.asyncio
async def test_delete_by_book_id_rejects_foreign_owner(db_session, test_user, user_factory):
    foreign = await user_factory()
    book = await _make_book(db_session, foreign.id)

    repo = ClassificationRecordRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.delete_by_book_id(book.id, owner_id=test_user.id)


@pytest.mark.asyncio
async def test_get_all_owned_by_book_id_success(db_session, test_user):
    # Owner has a book
    book = BookScanORM(title="OwnedBook", user_id=test_user.id)
    db_session.add(book)
    await db_session.flush()

    # Two records for that book
    rec1 = ClassificationRecordORM(book_scan_id=book.id)
    rec2 = ClassificationRecordORM(book_scan_id=book.id)
    db_session.add_all([rec1, rec2])
    await db_session.commit()

    repo = ClassificationRecordRepository(db_session)
    out = await repo.get_all_owned_by_book_id(book.id, owner_id=test_user.id)

    assert {r.id for r in out} == {rec1.id, rec2.id}


@pytest.mark.asyncio
async def test_get_all_owned_by_book_id_filters_out_foreign_records(db_session, test_user, user_factory):
    other = await user_factory()
    # Foreign user's book
    foreign_book = BookScanORM(title="ForeignBook", user_id=other.id)
    db_session.add(foreign_book)
    await db_session.flush()

    # Record belongs to foreign book
    rec = ClassificationRecordORM(book_scan_id=foreign_book.id)
    db_session.add(rec)
    await db_session.commit()

    repo = ClassificationRecordRepository(db_session)

    # Should return empty list, not raise
    out = await repo.get_all_owned_by_book_id(foreign_book.id, owner_id=test_user.id)

    assert out == []
