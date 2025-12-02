from unittest.mock import AsyncMock

import pytest

from app.infra.recipe_parser_mistral import MistralParser
from app.schemas.ocr import RecipeLLMOut


# --- Fakes for structured output ---
class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


@pytest.mark.asyncio
async def test_call_model_passes_messages_and_response_format():
    fake_client = AsyncMock()
    fake_client.chat = AsyncMock()
    content_model = RecipeLLMOut(title="Pancakes")
    fake_client.chat.parse_async = AsyncMock(return_value=FakeResponse(content_model))

    p = MistralParser(model="mistral-large-latest", api_key="DUMMY")
    p.client = fake_client

    out = await p.call_model("USER TEXT", "SYS INSTR", output_type=dict)

    # Assert: returned pydantic model, not dict
    assert isinstance(out, RecipeLLMOut)
    assert out.title == "Pancakes"

    fake_client.chat.parse_async.assert_awaited_once()
    kwargs = fake_client.chat.parse_async.await_args.kwargs
    assert kwargs["model"] == "mistral-large-latest"
    assert kwargs["messages"] == [
        {"role": "system", "content": "SYS INSTR"},
        {"role": "user", "content": "USER TEXT"},
    ]
    assert kwargs["response_format"] is dict


@pytest.mark.asyncio
async def test_call_model_propagates_sdk_errors():
    fake_client = AsyncMock()
    fake_client.chat = AsyncMock()
    fake_client.chat.parse_async = AsyncMock(side_effect=TimeoutError("boom"))

    p = MistralParser(api_key="DUMMY")
    p.client = fake_client

    with pytest.raises(TimeoutError, match="boom"):
        await p.call_model("x", "y", output_type=dict)


@pytest.mark.asyncio
async def test_call_model_uses_first_choice_only():
    class FakeResponse2:
        def __init__(self):
            self.choices = [
                FakeChoice(RecipeLLMOut(title="First")),
                FakeChoice(RecipeLLMOut(title="Second")),
            ]

    fake_client = AsyncMock()
    fake_client.chat = AsyncMock()
    fake_client.chat.parse_async = AsyncMock(return_value=FakeResponse2())

    p = MistralParser(api_key="DUMMY")
    p.client = fake_client

    out = await p.call_model("u", "s", output_type=dict)
    assert isinstance(out, RecipeLLMOut)
    assert out.title == "First"


@pytest.mark.asyncio
async def test_call_model_raises_if_no_choices():
    class EmptyResp:
        choices = []

    fake_client = AsyncMock()
    fake_client.chat = AsyncMock()
    fake_client.chat.parse_async = AsyncMock(return_value=EmptyResp())

    p = MistralParser(api_key="DUMMY")
    p.client = fake_client

    with pytest.raises(IndexError):
        await p.call_model("u", "s", output_type=dict)


@pytest.mark.asyncio
async def test_call_model_returns_raw_object_if_not_pydantic():
    class NoDump:
        pass

    fake_client = AsyncMock()
    fake_client.chat = AsyncMock()
    fake_client.chat.parse_async = AsyncMock(return_value=FakeResponse(NoDump()))

    p = MistralParser(api_key="DUMMY")
    p.client = fake_client

    out = await p.call_model("u", "s", output_type=dict)
    assert isinstance(out, NoDump)  # no exception, just a raw passthrough
