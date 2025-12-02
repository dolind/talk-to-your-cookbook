from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_postgres import PGVector

from app.ports.embedding_store import IEmbeddingStore, RecipeDocs


class PGVectorRetriever:
    def __init__(self, retriever: BaseRetriever):
        self._retriever = retriever

    def get_relevant_documents(self, query: str):
        docs = self._retriever.invoke(query)
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]


class PGVectorEmbeddingStore(IEmbeddingStore):
    """Allows us to store and retrieve embeddings in a vector store.
    PGVECTOR is a vector database that supports embeddings.
    In this app we have several vector stores, one for each model"""

    def __init__(self, pgvector: PGVector):
        self.vs = pgvector

    def add(self, docs: RecipeDocs) -> None:
        """This is the actual embedding method."""
        texts, metadatas, ids = docs.as_args()
        langchain_docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
        self.vs.add_documents(langchain_docs, ids=ids)

    def delete(self, ids: List[str]) -> None:
        self.vs.delete(ids=ids)

    def as_retriever(self, user_id: str, **kwargs) -> PGVectorRetriever:
        search_kwargs = {
            "k": 8,
            "fetch_k": 24,
            "lambda_mult": 0.5,
            "filter": {"user_id": user_id},
        }
        search_kwargs.update(kwargs)
        retriever = self.vs.as_retriever(search_type="mmr", search_kwargs=search_kwargs)
        return PGVectorRetriever(retriever)
