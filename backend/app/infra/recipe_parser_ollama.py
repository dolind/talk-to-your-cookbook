import logging
from typing import Any, Dict

import httpx

from app.ports.recipe_parser_llm import RecipeParserLLM

logger = logging.getLogger(__name__)


async def ensure_ollama_model(model: str, base_url: str):
    async with httpx.AsyncClient(timeout=None) as client:
        # Check model availability
        tags = await client.get(f"{base_url}/api/tags")
        installed = [m["name"] for m in tags.json().get("models", [])]

        if model not in installed:
            logger.info(f"Model missing, Pulling model {model}")
            await client.post(
                f"{base_url}/api/pull",
                json={"name": model},
            )


class OllamaParser(RecipeParserLLM):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def call_model(self, input_text: str, instruction: str, output_type) -> Dict[str, Any]:
        schema = output_type.model_json_schema()

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": input_text},
                    ],
                    # Use the new structured output format parameter
                    "format": schema,
                    "temperature": 0.2,  # deterministic
                    "stream": False,
                },
            )
            response.raise_for_status()
        content = response.json()["message"]["content"]
        print(content)
        return content
