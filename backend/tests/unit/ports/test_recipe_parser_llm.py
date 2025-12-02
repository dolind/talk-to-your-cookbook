from unittest.mock import patch

import pytest

from app.ports.recipe_parser_llm import (
    INSTRUCTION_PROMPT_LONG,
    RecipeParserLLM,
)

# this is where your RecipeLLMOut lives per your snippet
from app.schemas.ocr import RecipeLLMOut


class DummyParser(RecipeParserLLM):
    def __init__(self, reply="{}"):
        self.reply = reply
        self.seen = None

    async def call_model(self, input_text: str, instruction: str, output_type):
        # capture exactly what parse() passes
        self.seen = (input_text, instruction, output_type)
        return self.reply


@pytest.mark.asyncio
async def test_parse_calls_model_with_structured_prompt_and_output_type():
    parser = DummyParser(reply='{"ok": true}')
    # Patch postprocess in the SAME MODULE where parse() is defined
    with patch("app.ports.recipe_parser_llm.postprocess", return_value={"ok": True}) as pp:
        out = await parser.parse("RECIPE TEXT")

    # Asserts: correct prompt & output_type are passed through
    assert parser.seen == ("RECIPE TEXT", INSTRUCTION_PROMPT_LONG, RecipeLLMOut)
    pp.assert_called_once_with('{"ok": true}')
    assert out == {"ok": True}


@pytest.mark.asyncio
async def test_parse_propagates_call_model_error():
    class Failing(RecipeParserLLM):
        async def call_model(self, input_text: str, instruction: str, output_type):
            raise TimeoutError("boom")

    with pytest.raises(TimeoutError, match="boom"):
        await Failing().parse("x")


@pytest.mark.asyncio
async def test_parse_propagates_postprocess_error():
    parser = DummyParser(reply="not json")
    with patch("app.ports.recipe_parser_llm.postprocess", side_effect=ValueError("bad json")):
        with pytest.raises(ValueError, match="bad json"):
            await parser.parse("x")
