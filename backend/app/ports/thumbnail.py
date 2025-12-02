from abc import ABC, abstractmethod


class ThumbnailService(ABC):
    @abstractmethod
    async def generate_thumbnail(self, src_path: str) -> bytes:
        """
        Return thumbnail bytes suitable for writing with StorageService.save().
        The caller decides the final file name / path.
        """
        ...
