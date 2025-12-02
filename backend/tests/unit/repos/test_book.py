import pytest
from unit.repos.fakes import FakeResult, FakeSession

from app.models.ocr import BookScanORM
from app.repos.book import BookScanRepository
from app.schemas.ocr import BookScanCreate

# ---------------------------------------------------------------
# Fake SQLAlchemy Result & Session
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# Test: save()
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    dto = BookScanCreate(title="X")

    out = await repo.save(dto, owner_id="u1")

    assert out.title == "X"

    # Make sure DB interactions happened
    assert isinstance(db.added[0], BookScanORM)
    assert db.flushed == 1
    assert db.refreshed == [db.added[0]]
    assert db.committed == 1


# ---------------------------------------------------------------
# Test: get()
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_found_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    row = BookScanORM(id="b1", title="T", user_id="u1")

    # Store the next result we WANT to return
    next_result = FakeResult(scalar=row)

    async def fake_execute(stmt):
        # Whatever stmt repo creates, return the prebuilt result
        return next_result

    db.execute = fake_execute  # monkeypatch the method

    out = await repo.get("b1", "u1")

    assert out is not None
    assert out.id == "b1"
    assert out.title == "T"


@pytest.mark.asyncio
async def test_get_not_found_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    # Return a FakeResult with scalar=None => "not found"
    async def fake_execute(_):
        return FakeResult(scalar=None)

    db.execute = fake_execute

    out = await repo.get("missing", "u1")
    assert out is None


# ---------------------------------------------------------------
# Test: list_all()
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    row1 = BookScanORM(id="a", title="Alpha", user_id="u1")
    row2 = BookScanORM(id="z", title="Zeta", user_id="u1")

    async def fake_execute(_):
        return FakeResult(scalars=[row1, row2])

    db.execute = fake_execute

    results = await repo.list_all("u1")
    titles = [r.title for r in results]

    assert titles == ["Alpha", "Zeta"]


# ---------------------------------------------------------------
# Test: delete_if_unlinked()
# ---------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_if_unlinked_success_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    row = BookScanORM(id="b1", title="T", user_id="u1")
    row.images = []  # no linked images

    async def fake_execute(_):
        return FakeResult(scalar=row)

    db.execute = fake_execute

    result = await repo.delete_if_unlinked("b1", "u1")
    assert result is True
    assert db.deleted == [row]
    assert db.committed == 1


@pytest.mark.asyncio
async def test_delete_if_unlinked_not_found_unit():
    db = FakeSession()
    repo = BookScanRepository(db)

    async def fake_execute(_):
        return FakeResult(scalar=None)

    db.execute = fake_execute

    result = await repo.delete_if_unlinked("missing", "u1")
    assert result is False
