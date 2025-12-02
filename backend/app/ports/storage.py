from abc import ABC, abstractmethod
from typing import Any

from fastapi import UploadFile
from PIL import Image


class StorageService(ABC):
    @abstractmethod
    async def save_image(self, file: UploadFile, filename: str, kind: str = "recipe") -> str:
        """Save a binary image file. Returns full path or URI."""
        ...

    @abstractmethod
    async def save_binary_image(self, file: bytes, filename: str, kind: str = "recipe") -> str:
        """Save a binary image file. Returns full path or URI."""
        ...

    @abstractmethod
    async def load_image(self, file_id: str, kind: str = "recipe") -> Image.Image:
        """Load a binary image file. Returns full path or URI."""
        ...

    @abstractmethod
    async def delete(self, filename: str, kind: str = "recipe") -> None:
        """Delete a file (image or JSON) from storage."""
        ...

    @abstractmethod
    async def rename(self, storage_path: str, filename: str, kind: str = "recipe") -> str:
        """Rename a file in storage. Returns new full path or URI."""
        ...

    @abstractmethod
    async def get_image_path(self, image_id: str, kind: str = "recipe") -> str:
        """Get full path or URI for an image by its ID."""
        ...

    @abstractmethod
    async def copy_to_recipe(self, filename: str) -> str:
        """Copy an image from scanner_images → recipe_images.
        Returns the new path."""
        ...

    @abstractmethod
    async def get_json_path(self, image_id: str) -> str:
        """Get full path or URI for a json by its ID."""
        ...

    @abstractmethod
    async def save_json(self, data: Any, path: str) -> None:
        """Save a Python object as a JSON file to the given path."""
        ...

    @abstractmethod
    async def read_json(self, image_id: str) -> Any:
        """Read a JSON file and return its contents."""
        ...

    @abstractmethod
    def get_file_path(self, rel_path: str) -> str:
        """
        Returns an absolute path inside storage for any relative path.
        Example: storage.get_file_path("models/u2net.pth")
        """
        ...

    @abstractmethod
    async def save_file(self, data: bytes, rel_path: str) -> str:
        """
        Save raw bytes to a file under storage.
        Example: await storage.save_file(model_bytes, "models/u2net.pth")
        """
        ...
