from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Mapping, Protocol, Sequence


@dataclass
class RecipeDocs:
    texts: List[str]
    metas: List[Mapping[str, Any]]
    ids: List[str]

    def add(self, text: str, meta: Mapping[str, Any], doc_id: str) -> None:
        self.texts.append(text)
        self.metas.append(meta)
        self.ids.append(doc_id)

    def __post_init__(self):
        if not (len(self.texts) == len(self.metas) == len(self.ids)):
            raise ValueError(f"Length mismatch: texts={len(self.texts)}, metas={len(self.metas)}, ids={len(self.ids)}")

    def as_args(self) -> tuple[Sequence[str], Sequence[Mapping[str, Any]], Sequence[str]]:
        """Return a triple matching embedding_store.add(...) signature."""
        return self.texts, self.metas, self.ids


class IRetriever(Protocol):
    def get_relevant_documents(self, query: str): ...


class IEmbeddingStore(ABC):
    """Persist/retrieve chunk embeddings (per collection)."""

    @abstractmethod
    def add(self, docs: RecipeDocs) -> None: ...
    @abstractmethod
    def delete(self, ids: Sequence[str]) -> None: ...

    @abstractmethod
    def as_retriever(self, user_id: str, **kwargs) -> IRetriever: ...
