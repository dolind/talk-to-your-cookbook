import pytesseract
from PIL import Image, ImageOps

from app.ports.ocr import OCRService
from app.schemas.ocr import OCRResult


class PytesseractOCRService(OCRService):
    def __init__(self):
        pass

    async def extract(self, image_path: str, image_id: str) -> OCRResult:
        with Image.open(image_path) as img:
            image = ImageOps.exif_transpose(img).copy()

        # Full text content
        full_text = pytesseract.image_to_string(image)

        # Word-level and block-level data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Convert pytesseract blocks into a compatible structure
        blocks = []
        for i in range(len(data["level"])):
            if data["level"][i] == 2:  # 2 = block level in Tesseract hierarchy
                block = {
                    "blockType": "TEXT",
                    "boundingBox": {
                        "vertices": [
                            {"x": data["left"][i], "y": data["top"][i]},
                            {"x": data["left"][i] + data["width"][i], "y": data["top"][i]},
                            {"x": data["left"][i] + data["width"][i], "y": data["top"][i] + data["height"][i]},
                            {"x": data["left"][i], "y": data["top"][i] + data["height"][i]},
                        ]
                    },
                    "text": "",  # Tesseract does not group text by block in this API
                }
                blocks.append(block)

        return OCRResult(page_id=image_id, blocks=blocks, full_text=full_text)
