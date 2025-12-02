import json
from base64 import b64encode
from io import BytesIO

import requests
from PIL import Image, ImageOps

from app.ports.ocr import OCRService
from app.schemas.ocr import OCRResult


class GoogleVisionOCRService(OCRService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint_url = "https://vision.googleapis.com/v1/images:annotate"

    async def extract(self, image_path: str, image_id: str) -> OCRResult:
        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img).copy()
        buf = BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()
        image_content = b64encode(image_bytes).decode()

        # Build the request
        request_body = {
            "requests": [{"image": {"content": image_content}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]
        }

        response = requests.post(
            self.endpoint_url,
            data=json.dumps(request_body),
            params={"key": self.api_key},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code != 200:
            raise RuntimeError(f"Google Vision API error: {response.status_code}, {response.text}")

        result = response.json()
        if "error" in result.get("responses", [{}])[0]:
            raise RuntimeError(f"Google Vision API returned error: {result['responses'][0]['error']}")

        if "fullTextAnnotation" in result["responses"][0]:
            full_text = result["responses"][0]["fullTextAnnotation"]["text"]
            blocks = result["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"]
            return OCRResult(page_id=image_id, blocks=blocks, full_text=full_text)
        else:
            return OCRResult(page_id=image_id, blocks=[], full_text="")
