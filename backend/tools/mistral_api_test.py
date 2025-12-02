import asyncio
import json

from dotenv import load_dotenv

from app.core.config import Settings
from app.infra.recipe_parser_mistral import MistralParser

load_dotenv()


async def main():
    settings = Settings()

    service = MistralParser(model=settings.CHAT_MODEL_MISTRAL, api_key=settings.MISTRAL_API_KEY)

    with open("tests/integration/data/google_vision_response.json", "r") as f:
        content = json.load(f)
        result = await service.parse(content["full_text"])

        with open("tests/integration/data/mistral_response.json", "w", encoding="utf-8") as f2:
            json.dump(result, f2, indent=2, ensure_ascii=False)  # or custom serialization


if __name__ == "__main__":
    asyncio.run(main())
