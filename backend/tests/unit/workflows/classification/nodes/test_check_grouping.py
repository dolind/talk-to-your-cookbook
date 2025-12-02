import pytest

from app.schemas.ocr import (
    ClassificationGraphState,
    ClassificationRecordInputPage,
    GroupApproval,
    Page,
    PageType,
)
from app.workflows.classification.nodes.check_grouping import check_grouping


class FakeImageRepo:
    def __init__(self, pages_by_id=None, error_ids=None):
        self.pages_by_id = pages_by_id or {}
        self.error_ids = set(error_ids or [])
        self.calls = []

    async def get_owned(self, page_id: str, owner_id: str):
        self.calls.append((page_id, owner_id))
        if page_id in self.error_ids:
            raise RuntimeError(f"boom for {page_id}")
        return self.pages_by_id.get(page_id)


def make_input_page(pid: str, page_number: int, page_type: PageType = PageType.TEXT):
    return ClassificationRecordInputPage(
        original_id=pid,
        page_number=page_number,
        page_type=page_type,
        ocr_path=None,
        title=None,
        segmentation_done=False,
    )


@pytest.mark.asyncio
async def test_check_grouping_reject(monkeypatch):
    """If user_response.approved == False -> current_recipe_state is None."""

    def fake_interrupt(payload):
        return {"response_to_approve_grouping": GroupApproval(approved=False)}

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    state = ClassificationGraphState(input_pages=[])

    out = await check_grouping(state, {"configurable": {}})

    assert out == {"current_recipe_state": None}


@pytest.mark.asyncio
async def test_check_grouping_approved_no_new_group(monkeypatch):
    """Approved with new_group=None => keep existing input_pages unchanged."""
    pages = [make_input_page("p1", 1), make_input_page("p2", 2)]

    def fake_interrupt(payload):
        return {"response_to_approve_grouping": GroupApproval(approved=True, new_group=None)}

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    state = ClassificationGraphState(input_pages=pages)

    out = await check_grouping(state, {"configurable": {"image_repo": None, "owner_id": "u"}})

    assert out["input_pages"] == pages


@pytest.mark.asyncio
async def test_check_grouping_approved_same_group(monkeypatch):
    """Approved, new_group identical (by id + page_number) => no change."""
    pages = [make_input_page("p1", 1), make_input_page("p2", 2)]

    new_group = [
        Page(id="p1", page_number=1),
        Page(id="p2", page_number=2),
    ]

    def fake_interrupt(payload):
        return {
            "response_to_approve_grouping": GroupApproval(
                approved=True,
                new_group=new_group,
            )
        }

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    state = ClassificationGraphState(input_pages=pages)

    out = await check_grouping(state, {"configurable": {"image_repo": None, "owner_id": "u"}})

    # Should just return the original list
    assert out["input_pages"] == pages


@pytest.mark.asyncio
async def test_check_grouping_remove_page(monkeypatch):
    """User new_group missing a page => that page is removed from input_pages."""
    p1 = make_input_page("p1", 1)
    p2 = make_input_page("p2", 2)
    state = ClassificationGraphState(input_pages=[p1, p2])

    new_group = [
        Page(id="p2", page_number=2),  # only p2 kept
    ]

    def fake_interrupt(payload):
        return {
            "response_to_approve_grouping": GroupApproval(
                approved=True,
                new_group=new_group,
            )
        }

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    out = await check_grouping(
        state,
        {"configurable": {"image_repo": None, "owner_id": "u"}},
    )

    input_pages = out["input_pages"]
    assert len(input_pages) == 1
    assert input_pages[0].original_id == "p2"


@pytest.mark.asyncio
async def test_check_grouping_add_new_page(monkeypatch):
    """User adds a new page id -> image_repo.get_owned is called and page is appended & ordered."""
    p1 = make_input_page("p1", 1)
    state = ClassificationGraphState(input_pages=[p1])

    new_group = [
        Page(id="p2", page_number=2),
        Page(id="p1", page_number=1),
    ]

    def fake_interrupt(payload):
        return {
            "response_to_approve_grouping": GroupApproval(
                approved=True,
                new_group=new_group,
            )
        }

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    # Fake repo returns a minimal page object for p2
    owned_p2 = type(
        "OwnedPage",
        (),
        {
            "id": "p2",
            "page_number": 2,
            "page_type": PageType.TEXT,
            "ocr_path": None,
            "title": "new",
            "segmentation_done": False,
        },
    )()
    repo = FakeImageRepo(pages_by_id={"p2": owned_p2})

    out = await check_grouping(
        state,
        {"configurable": {"image_repo": repo, "owner_id": "u"}},
    )

    input_pages = out["input_pages"]
    # Should now contain p2 + p1 in order of new_group ids
    assert [p.original_id for p in input_pages] == ["p2", "p1"]
    # get_owned must have been called for p2
    assert repo.calls == [("p2", "u")]


@pytest.mark.asyncio
async def test_check_grouping_add_new_page_repo_error(monkeypatch):
    """
    If image_repo.get_owned raises, check_grouping should swallow the error
    and still return a valid input_pages list with existing pages only.
    """
    p1 = make_input_page("p1", 1)
    state = ClassificationGraphState(input_pages=[p1])

    new_group = [Page(id="p2", page_number=2)]  # new id only

    def fake_interrupt(payload):
        return {
            "response_to_approve_grouping": GroupApproval(
                approved=True,
                new_group=new_group,
            )
        }

    monkeypatch.setattr(
        "app.workflows.classification.nodes.check_grouping.interrupt",
        fake_interrupt,
    )

    repo = FakeImageRepo(pages_by_id={}, error_ids={"p2"})

    out = await check_grouping(
        state,
        {"configurable": {"image_repo": repo, "owner_id": "u"}},
    )

    # Because p2 failed to load, and p1 isn't in new_ids, result should be empty
    input_pages = out["input_pages"]
    assert input_pages == []
    # We did attempt to fetch p2
    assert repo.calls == [("p2", "u")]
