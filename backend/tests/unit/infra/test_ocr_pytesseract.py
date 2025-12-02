from types import SimpleNamespace

import pytest
from PIL import Image

import app.infra.ocr_pytesseract as ocr


@pytest.mark.asyncio
async def test_extract_builds_blocks_and_full_text(monkeypatch, tmp_path):
    image_path = tmp_path / "img.jpg"

    # Prepare a fake image file PIL can open
    img = Image.new("RGB", (10, 10), color="white")
    img.save(image_path)

    # Sentinel image returned after EXIF transpose
    sentinel_img = object()

    # Monkeypatch exif_transpose -> returns sentinel
    def fake_exif_transpose(pil_img):
        return SimpleNamespace(copy=lambda: sentinel_img)

    monkeypatch.setattr(ocr.ImageOps, "exif_transpose", fake_exif_transpose)

    # Fake OCR output
    full_text = "some full text"

    def fake_image_to_string(image):
        assert image is sentinel_img
        return full_text

    # Word-level data including two block-level entries (level == 2)
    data = {
        "level": [1, 2, 3, 2],
        "left": [0, 10, 20, 30],
        "top": [0, 5, 15, 25],
        "width": [0, 100, 50, 75],
        "height": [0, 40, 20, 35],
    }

    def fake_image_to_data(image, output_type):
        assert image is sentinel_img
        assert output_type == "DICT"
        return data

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", fake_image_to_string)
    monkeypatch.setattr(ocr.pytesseract, "image_to_data", fake_image_to_data)
    monkeypatch.setattr(ocr.pytesseract, "Output", SimpleNamespace(DICT="DICT"))

    service = ocr.PytesseractOCRService()
    result = await service.extract(str(image_path), "page-1")

    assert result.page_id == "page-1"
    assert result.full_text == full_text

    # Expect two blocks (level == 2)
    assert len(result.blocks) == 2
    assert result.blocks[0] == {
        "blockType": "TEXT",
        "boundingBox": {
            "vertices": [
                {"x": 10, "y": 5},
                {"x": 110, "y": 5},
                {"x": 110, "y": 45},
                {"x": 10, "y": 45},
            ]
        },
        "text": "",
    }

    # Sanity-check second block’s bottom-right vertex
    assert result.blocks[1]["boundingBox"]["vertices"][2] == {"x": 105, "y": 60}


@pytest.mark.asyncio
async def test_extract_with_no_block_levels(monkeypatch, tmp_path):
    image_path = tmp_path / "img.jpg"

    img = Image.new("RGB", (10, 10), color="white")
    img.save(image_path)

    sentinel_img = object()
    monkeypatch.setattr(
        ocr.ImageOps,
        "exif_transpose",
        lambda pil: SimpleNamespace(copy=lambda: sentinel_img),
    )

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", lambda img: "")

    def fake_image_to_data(image, output_type=None, **kwargs):
        return {"level": [], "left": [], "top": [], "width": [], "height": []}

    monkeypatch.setattr(ocr.pytesseract, "image_to_data", fake_image_to_data)
    monkeypatch.setattr(ocr.pytesseract, "Output", SimpleNamespace(DICT="DICT"))

    service = ocr.PytesseractOCRService()
    result = await service.extract(str(image_path), "page-2")

    assert result.page_id == "page-2"
    assert result.full_text == ""
    assert result.blocks == []
