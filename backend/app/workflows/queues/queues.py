import asyncio
from dataclasses import dataclass
from typing import List

from app.schemas.embeddings import EmbeddingJob
from app.schemas.ocr import PageScanRead


@dataclass
class ClassificationJob:
    pages: List[PageScanRead]
    owner_id: str


@dataclass
class QueueRegistry:
    ocr: asyncio.Queue[PageScanRead]
    seg: asyncio.Queue[PageScanRead]
    cls: asyncio.Queue[ClassificationJob]
    emb: asyncio.Queue[EmbeddingJob]


_default_registry = QueueRegistry(asyncio.Queue(), asyncio.Queue(), asyncio.Queue(), asyncio.Queue())


def get_queue_registry() -> QueueRegistry:
    return _default_registry
