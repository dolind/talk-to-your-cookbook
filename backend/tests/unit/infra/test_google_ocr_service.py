import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from conftest import get_test_file

from app.infra.ocr_google import GoogleVisionOCRService
from app.schemas.ocr import OCRResult


@pytest.fixture
def mock_image():
    mock_img = MagicMock()
    mock_img._getexif.return_value = {274: 1}  # Normal orientation
    buffer = BytesIO()
    buffer.write(b"image_bytes_result")
    buffer.seek(0)
    mock_img.save.side_effect = lambda buf, format: buf.write(b"image_bytes_result")
    return mock_img


@patch("app.infra.ocr_pytesseract.Image.open")
@patch("requests.post")
@pytest.mark.asyncio
async def test_extract_api_error(mock_post, mock_image_open, mock_image):
    mock_image_open.return_value = mock_image
    service = GoogleVisionOCRService(api_key="fake-api-key")

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError, match="Google Vision API error: 500"):
        await service.extract("fake_path.jpg", "image-id")


@patch("app.infra.ocr_pytesseract.Image.open")
@patch("requests.post")
@pytest.mark.asyncio
async def test_extract_with_error_in_response(mock_post, mock_image_open, mock_image):
    mock_image_open.return_value = mock_image
    service = GoogleVisionOCRService(api_key="fake-api-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"responses": [{"error": {"message": "Invalid image format"}}]}
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError, match="Google Vision API returned error:"):
        await service.extract("fake_path.jpg", "image-id")


@patch("app.infra.ocr_pytesseract.Image.open")
@patch("requests.post")
@pytest.mark.asyncio
async def test_extract_no_full_text_annotation(mock_post, mock_image_open, mock_image):
    mock_image_open.return_value = mock_image
    service = GoogleVisionOCRService(api_key="fake-api-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"responses": [{}]}  # No fullTextAnnotation
    mock_post.return_value = mock_response

    result = await service.extract("fake_path.jpg", "image-id")
    assert isinstance(result, OCRResult)
    assert result.page_id == "image-id"
    assert result.full_text == ""
    assert result.blocks == []
