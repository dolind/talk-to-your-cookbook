import json
import os
import shutil
from io import BytesIO
from typing import Any

import aiofiles
from fastapi import UploadFile
from PIL import Image

from app.ports.storage import StorageService


class LocalStorageService(StorageService):
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.recipe_image_dir = os.path.join(base_path, "images")
        self.scanner_image_dir = os.path.join(base_path, "scanner_images")
        self.json_dir = os.path.join(base_path, "ocr")
        for folder in [self.recipe_image_dir, self.scanner_image_dir, self.json_dir]:
            os.makedirs(folder, exist_ok=True)

    def _get_dir(self, kind: str) -> str:
        return self.scanner_image_dir if kind == "scanner" else self.recipe_image_dir

    async def save_image(self, file: UploadFile, filename: str, kind: str = "recipe") -> str:
        path = os.path.join(self._get_dir(kind), filename)
        async with aiofiles.open(path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                await out.write(chunk)
        return path

    async def save_binary_image(self, file_bytes: bytes, filename: str, kind: str = "recipe") -> str:
        path = os.path.join(self._get_dir(kind), filename)

        async with aiofiles.open(path, "wb") as f:
            await f.write(file_bytes)

        return path

    async def load_image(self, file_id: str, kind: str = "recipe") -> Image.Image:
        path = os.path.join(self._get_dir(kind), f"{file_id}.jpg")
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()
        return Image.open(BytesIO(data))

    async def delete(self, filename: str, kind: str = "recipe") -> None:
        for folder in [self._get_dir(kind), self.json_dir]:
            path = os.path.join(folder, filename)
            if os.path.exists(path):
                os.remove(path)

    async def rename(self, storage_path: str, filename: str, kind: str = "recipe") -> str:
        new_path = os.path.join(self._get_dir(kind), filename)
        os.rename(storage_path, new_path)
        return new_path

    async def get_image_path(self, image_id: str, kind: str = "recipe") -> str:
        # image ID is the filename with extension
        return os.path.join(self._get_dir(kind), f"{image_id}.jpg")

    async def copy_to_recipe(self, filename: str) -> str:
        """
        Copy an image from scanner_images → recipe_images.
        Returns the new path.
        """
        src = os.path.join(self.scanner_image_dir, filename)
        dest = os.path.join(self.recipe_image_dir, filename)

        if not os.path.exists(src):
            raise FileNotFoundError(f"Scanner image not found: {src}")

        shutil.copy(src, dest)
        return dest

    # --- JSON ---

    async def get_json_path(self, image_id: str) -> str:
        return os.path.join(self.json_dir, f"{image_id}.json")

    async def save_json(self, data: Any, image_id: str) -> None:
        path = os.path.join(self.json_dir, f"{image_id}.json")
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(
                json.dumps(
                    data,
                    ensure_ascii=False,
                )
            )

    async def read_json(self, image_id: str) -> Any:
        path = os.path.join(self.json_dir, f"{image_id}.json")
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            contents = await f.read()
        return json.loads(contents)

    # --- Generic files / models ---

    def get_file_path(self, rel_path: str) -> str:
        """
        Returns an absolute path inside storage for any relative path.
        Example: storage.get_file_path("models/u2net.pth")
        """
        return os.path.join(self.base_path, rel_path)

    async def save_file(self, data: bytes, rel_path: str) -> str:
        """
        Save raw bytes to a file under storage.
        Example: await storage.save_file(model_bytes, "models/u2net.pth")
        """
        abs_path = self.get_file_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(data)
        return abs_path
