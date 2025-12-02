import torch
from langchain_core.embeddings import Embeddings
from langchain_mistralai import MistralAIEmbeddings
from langchain_postgres import PGVector
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

settings = get_settings()


class LocalBgeEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = None):
        self.model = SentenceTransformer(model_name, device=device or ("cuda" if torch.cuda.is_available() else "cpu"))

    def embed_documents(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text):
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()


def _build_vector_store(target: str, version: str) -> PGVector:
    """
    Build a PGVector store for a specific target and version.
    """
    collection_name = settings.collection_name(target, version)

    # Pick embedding function based on target
    if target == "local_bge":
        embeddings = LocalBgeEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    elif target == "mistralai":
        embeddings = MistralAIEmbeddings(model=settings.EMBEDDING_MODELS[target]["model_name"])
    else:
        raise ValueError(f"Unknown embedding target: {target}")

    return PGVector(
        connection=settings.pgvector_dsn,
        collection_name=collection_name,
        embeddings=embeddings,
    )


def build_store_registry():
    """
    Returns a dict of PGVector stores keyed by "target:version",
    e.g., "local_bge:v1" and "mistralai: v1
    including active and optional staged versions.
    """
    registry: dict[str, PGVector] = {}
    for target, config in settings.target_config_list.items():
        # Active version
        registry[f"{target}:{config.active_version}"] = _build_vector_store(target, config.active_version)

        # Optional staged version if different from an active version
        if config.staged_version != config.active_version:
            registry[f"{target}:{config.staged_version}"] = _build_vector_store(target, config.staged_version)
    return registry
