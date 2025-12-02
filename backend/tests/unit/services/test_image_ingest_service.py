import asyncio
import io
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.schemas.ocr import PageScanRead
from app.services.image_ingest_service import ImageIngestService


@pytest.mark.asyncio
async def test_ingest_pages():
    # Setup mock services
    mock_storage = AsyncMock()
    mock_repo = AsyncMock()
    mock_queue = asyncio.Queue()

    # Sample UploadFile
    file = UploadFile(filename="page.jpg", file=io.BytesIO(b"fake image data"))
    files = [file]

    scan_id = "scan-123"
    owner_id = "user-123"
    tmp_path = "/tmp/tmp-123.jpg"
    final_path = "/tmp/image-abc.jpg"

    # Fake image row from DB
    image_row = PageScanRead(
        id="img-abc", filename="tmp.jpg", bookScanID=scan_id, page_number=0, scanDate=datetime.now()
    )
    updated_row = PageScanRead(
        id="img-abc", filename="img-abc.jpg", bookScanID=scan_id, page_number=0, scanDate=datetime.now()
    )

    # Mock behavior
    mock_storage.save_image.return_value = tmp_path
    mock_repo.save.return_value = image_row
    mock_storage.rename.return_value = final_path
    mock_repo.update.return_value = updated_row

    # Create service
    service = ImageIngestService(storage=mock_storage, image_repo=mock_repo, queue=mock_queue)

    # Act
    result = await service.ingest_pages(scan_id=scan_id, files=files, owner_id=owner_id)

    # Assert
    assert result == ["img-abc"]
    assert mock_storage.save_image.called
    mock_repo.save.assert_awaited_once()
    save_args, _ = mock_repo.save.call_args
    assert save_args[1] == owner_id
    assert mock_storage.rename.called
    mock_repo.update.assert_awaited_once()
    update_args, _ = mock_repo.update.call_args
    assert update_args[1] == owner_id

    # Verify queue got item
    queued_item = await mock_queue.get()
    assert queued_item.id == "img-abc"
    assert queued_item.filename == "img-abc.jpg"
