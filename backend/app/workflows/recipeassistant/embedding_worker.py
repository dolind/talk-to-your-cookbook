import asyncio
import logging
from typing import Dict, Optional, Tuple, cast, get_args

from app.ports.embedding_store import IEmbeddingStore
from app.schemas.embeddings import EmbeddingJob, EmbeddingPipelineTargets
from app.services.embedding_service import EmbeddingService
from app.workflows.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class EmbeddingWorker(BaseWorker[EmbeddingJob]):
    def __init__(
        self,
        entry_queue: asyncio.Queue[EmbeddingJob],
        service: EmbeddingService,
        stores: Dict[str, IEmbeddingStore],
        current_version: str,
        worker_name: Optional[str] = None,
    ):
        super().__init__(entry_queue, worker_name or "EmbeddingWorker")
        self.service = service
        self.stores = stores
        logger.info(f"Embedding worker uses these stores: {list(self.stores.keys())}")
        self.current_version = current_version

    async def handle(self, job: EmbeddingJob):
        version = job.version or self.current_version
        default_targets: Tuple[str, ...] = cast(Tuple[str, ...], get_args(EmbeddingPipelineTargets))
        targets = list(job.targets) if job.targets else list(default_targets)
        vector_store_keys = [f"{t}:{version}" for t in targets]
        logger.info("Embedding targets: %s", vector_store_keys)
        used = [self.stores[k] for k in vector_store_keys if k in self.stores]
        if not used:
            logger.warning("No stores resolved for job %s", job.model_dump())
            return
        for store in used:
            n = await self.service.index(store, job.recipe_id, job.user_id, reindex=job.reindex)
            logger.info("Indexed %s chunks into %s", n, getattr(store, "vs", store))
