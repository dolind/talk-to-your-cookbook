import asyncio
import json

from dotenv import load_dotenv

from app.core.config import Settings
from app.infra.recipe_parser_ollama import OllamaParser  # update import!

load_dotenv()


async def main():
    settings = Settings()

    parser = OllamaParser(
        base_url=settings.OLLAMA_URL,
        model=settings.CHAT_MODEL_OLLAMA,
    )

    with open("tests/data/google_vision_response.json", "r") as f:
        content = json.load(f)
        result = await parser.parse(content["full_text"])

    with open("tests/data/ollama_response.json", "w", encoding="utf-8") as f2:
        json.dump(result, f2, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
