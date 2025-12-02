from abc import ABC, abstractmethod
from typing import List


class IChunker(ABC):
    @abstractmethod
    def split(self, text: str) -> List[str]: ...
