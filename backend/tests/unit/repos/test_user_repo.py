import pytest
import pytest_asyncio
from unit.repos.fakes import FakeResult, FakeSession

from app.models.user import User
from app.repos.user import UserRepository

# -----------------------------------------------------
# Fixtures
# -----------------------------------------------------


@pytest_asyncio.fixture
async def sample_user():
    return User(id="123", email="a@example.com")


# -----------------------------------------------------
# exists_by_email()
# -----------------------------------------------------


@pytest.mark.parametrize(
    "scalars, expected",
    [
        ([User(id="1", email="x@test.com")], True),
        ([], False),
    ],
)
@pytest.mark.asyncio
async def test_exists_by_email(scalars, expected):
    session = FakeSession(execute_return=FakeResult(scalars=scalars))
    repo = UserRepository(session)

    result = await repo.exists_by_email("x@test.com")
    assert result is expected


@pytest.mark.asyncio
async def test_get_by_email_returns_user():
    user = User(id="1", email="a@example.com")
    session = FakeSession(execute_return=FakeResult(scalars=[user]))
    repo = UserRepository(session)

    result = await repo.get_by_email("a@example.com")
    assert result is user


@pytest.mark.asyncio
async def test_get_by_email_returns_none():
    session = FakeSession(execute_return=FakeResult(scalars=[]))
    repo = UserRepository(session)

    result = await repo.get_by_email("missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_user():
    user = User(id="123", email="a@example.com")
    session = FakeSession(execute_return=FakeResult(scalars=[user]))
    repo = UserRepository(session)

    result = await repo.get_by_id("123")
    assert result is user


# -----------------------------------------------------
# create()
# -----------------------------------------------------


@pytest.mark.asyncio
async def test_create_commits_and_refreshes(sample_user):
    session = FakeSession()
    repo = UserRepository(session)

    result = await repo.create(sample_user)

    assert session.added == [sample_user]
    assert session.committed == 1
    assert session.refreshed == [sample_user]
    assert result is sample_user


# -----------------------------------------------------
# update()
# -----------------------------------------------------


@pytest.mark.asyncio
async def test_update_commits_and_refreshes(sample_user):
    session = FakeSession()
    repo = UserRepository(session)

    result = await repo.update(sample_user)

    assert session.committed == 1
    assert session.refreshed == [sample_user]
    assert result is sample_user
