import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from app.schemas.ocr import RecipeLLMOut


def postprocess(response_text: str) -> dict:
    try:
        # Strip markdown if model wraps in ```json
        if response_text.startswith("```json"):
            response_text = response_text.strip("`").split("json", 1)[-1].strip()
        elif response_text.startswith("```"):
            response_text = response_text.strip("`").split(None, 1)[-1].strip()

        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output as JSON: {e}\nRaw response:\n{response_text}") from e


INSTRUCTION_PROMPT_LONG = """
You are a recipe extraction assistant.

Analyze unstructured recipe text and convert it into structured JSON.

Return ONLY a valid JSON object. No markdown, no prose, no comments.

Follow this exact schema and include ALL fields:

{
  "title": string,
  "description": string | null,
  "ingredients": [
    {
      "name": string,
      "quantity": string | null,
      "unit": string | null,
      "preparation": string | null,
      "notes": string | null
    }
  ],
  "instructions": [ string ],
  "prep_time": string | null,
  "cook_time": string | null,
  "servings": string | null,
  "notes": string | null
}

Rules:
- If multiple recipes appear, extract only the first one.
- Use null for missing values.
- Do not invent ingredients or steps that are not in the text.
- Preserve the original language.
- Do not include fields not shown in the schema.
"""

INSTRUCTION_PROMPT_SHORT = (
    'Users provides recipe. Convert the recipe to JSON using the "https://schema.org/Recipe" format.'
    " Only return the JSON."
)


INSTRUCTION_PROMPT_STRUCTURED = (
    "Extract a single recipe from the text (use the first if multiple). "
    "Return JSON matching the provided schema. No markdown or explanations. "
    "If times are not explicitly stated, check instructions."
    "Use null for unknowns. Preserve the original language."
)

"""
A class with the responsibility to create a json from unstructured text with the help of an llm.
 simple relies on prompts
"""


class RecipeParserLLM(ABC):
    @abstractmethod
    async def call_model(self, input_text: str, instruction: str, output_type) -> str: ...

    async def parse(self, recipe_text: str) -> Dict[str, Any]:
        reply = await self.call_model(
            input_text=recipe_text, instruction=INSTRUCTION_PROMPT_LONG, output_type=RecipeLLMOut
        )
        parsed_json = postprocess(reply)
        return parsed_json
