from typing import Any, Dict

from mistralai import Mistral

from app.ports.recipe_parser_llm import RecipeParserLLM


class MistralParser(RecipeParserLLM):
    def __init__(self, model: str = "mistral-large-latest", api_key: str = ""):
        self.client = Mistral(api_key=api_key)
        self.model = model

    async def call_model(self, input_text: str, instruction: str, output_type) -> Dict[str, Any]:
        chat_response = await self.client.chat.parse_async(
            model=self.model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": input_text},
            ],
            response_format=output_type,
        )

        return chat_response.choices[0].message.content
