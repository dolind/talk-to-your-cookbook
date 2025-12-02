import asyncio
import json

from dotenv import load_dotenv

from app.core.config import Settings
from app.infra.ocr_google import GoogleVisionOCRService

load_dotenv()


async def async_main():
    settings = Settings()
    service = GoogleVisionOCRService(api_key=settings.GOOGLE_API_KEY)
    result = await service.extract("tests/data/storage/pages/text_0.png", image_id="test-page-id")

    # Save raw JSON response from requests.post().json()
    with open("tests/data/google_vision_response.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)  # or custom serialization


asyncio.run(async_main())
