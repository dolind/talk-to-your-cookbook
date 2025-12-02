import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseWorker(ABC, Generic[T]):  # pragma: no cover
    def __init__(self, entry_queue: asyncio.Queue[T], worker_name: Optional[str] = None):
        self.entry_queue = entry_queue
        self._hb: Optional[asyncio.Task] = None
        self.worker_name = worker_name or self.__class__.__name__

    async def _heartbeat(self):
        try:
            while True:
                await asyncio.sleep(2)
                logger.debug(f"{self.worker_name} - heartbeat: qsize={self.entry_queue.qsize()}")
        except asyncio.CancelledError:
            logger.info(f"{self.worker_name} - heartbeat cancelled")

    async def run(self):
        self._hb = asyncio.create_task(self._heartbeat())
        logger.info(f"{self.worker_name} - Starting run loop")
        try:
            while True:
                logger.info(f"{self.worker_name} - Waiting for next task")
                task = await self.entry_queue.get()
                try:
                    await self.handle(task)
                except Exception as e:
                    logger.exception(f"{self.worker_name} - Failed to process task: {e}")
                finally:
                    self.entry_queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"{self.worker_name} - Shutdown signal received")
            raise
        finally:
            if self._hb:
                self._hb.cancel()
                with suppress(asyncio.CancelledError):
                    await self._hb

    @abstractmethod
    async def handle(self, item: T): ...
