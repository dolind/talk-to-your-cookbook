import pytest

from app.schemas.ocr import ClassificationGraphState
from app.workflows.classification.nodes.interrupt_taxonomy import interrupt_taxonomy


@pytest.mark.asyncio
async def test_interrupt_taxonomy(monkeypatch):
    def fake_interrupt(payload):
        return {"response_to_approve_taxonomy": type("Resp", (), {"categories": ["A"], "tags": ["B"]})}

    monkeypatch.setattr(
        "app.workflows.classification.nodes.interrupt_taxonomy.interrupt",
        fake_interrupt,
    )

    state = ClassificationGraphState()
    out = await interrupt_taxonomy(state)

    assert out == {"taxonomy_user_approved": {"categories": ["A"], "tags": ["B"]}}
