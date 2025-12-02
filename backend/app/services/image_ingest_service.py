import asyncio
from datetime import datetime

from fastapi import UploadFile

from app.ports.storage import StorageService
from app.repos.image_repo import ImageRepository
from app.schemas.ocr import PageScanCreate, PageScanRead, PageScanUpdate


class ImageIngestService:
    def __init__(
        self,
        storage: StorageService,
        image_repo: ImageRepository,
        queue: asyncio.Queue[PageScanRead],
    ):
        self.storage = storage
        self.image_repo = image_repo
        self.queue = queue

    async def ingest_pages(self, scan_id: str, files: list[UploadFile], owner_id: str) -> list[str]:
        page_ids = []
        for file in files:
            tmp_filename = f"tmp-{datetime.now().timestamp():.0f}.jpg"
            tmp = await self.storage.save_image(file, tmp_filename, "scanner")
            image_row = await self.image_repo.save(PageScanCreate(filename=tmp, bookScanID=scan_id), owner_id)
            final_name = f"{image_row.id}.jpg"

            await self.storage.rename(tmp, final_name, "scanner")

            dto = await self.image_repo.update(PageScanUpdate(id=image_row.id, filename=final_name), owner_id)

            await self.queue.put(dto)
            page_ids.append(image_row.id)
        return page_ids
