from types import SimpleNamespace

from langchain_core.documents import Document

from app.infra.embeding_vectorstore_langchain import PGVectorEmbeddingStore, PGVectorRetriever

# ----------------------------------------------------------
# Helper Fake RecipeDocs
# ----------------------------------------------------------


class FakeRecipeDocs:
    def __init__(self, texts, metas, ids):
        self._texts = texts
        self._metas = metas
        self._ids = ids

    def as_args(self):
        return self._texts, self._metas, self._ids


# ----------------------------------------------------------
# Tests for PGVectorRetriever
# ----------------------------------------------------------


def test_pgvector_retriever_returns_clean_dicts():
    # fake underlying retriever
    fake_docs = [
        Document(page_content="A", metadata={"x": 1}),
        Document(page_content="B", metadata={"y": 2}),
    ]
    fake_retriever = SimpleNamespace(invoke=lambda q: fake_docs)

    retriever = PGVectorRetriever(fake_retriever)
    out = retriever.get_relevant_documents("query text")

    assert out == [
        {"content": "A", "metadata": {"x": 1}},
        {"content": "B", "metadata": {"y": 2}},
    ]


# ----------------------------------------------------------
# Tests for PGVectorEmbeddingStore.add
# ----------------------------------------------------------


def test_embedding_store_add_calls_pgvector_correctly():
    calls = {}

    # fake pgvector with record of calls
    class FakePGVector:
        def add_documents(self, langchain_docs, ids):
            calls["docs"] = langchain_docs
            calls["ids"] = ids

    store = PGVectorEmbeddingStore(FakePGVector())

    docs = FakeRecipeDocs(
        texts=["text1", "text2"],
        metas=[{"a": 1}, {"b": 2}],
        ids=["i1", "i2"],
    )

    store.add(docs)

    # verify correct structure passed to pgvector
    assert calls["ids"] == ["i1", "i2"]
    assert len(calls["docs"]) == 2
    assert isinstance(calls["docs"][0], Document)
    assert calls["docs"][0].page_content == "text1"
    assert calls["docs"][0].metadata == {"a": 1}


# ----------------------------------------------------------
# Tests for PGVectorEmbeddingStore.delete
# ----------------------------------------------------------


def test_embedding_store_delete_calls_pgvector():
    calls = {}

    class FakePGVector:
        def delete(self, ids):
            calls["ids"] = ids

    store = PGVectorEmbeddingStore(FakePGVector())
    store.delete(["a", "b"])

    assert calls["ids"] == ["a", "b"]


# ----------------------------------------------------------
# Tests for PGVectorEmbeddingStore.as_retriever
# ----------------------------------------------------------


def test_embedding_store_as_retriever_wraps_retriever():
    calls = {}

    class FakePGVector:
        def as_retriever(self, search_type, search_kwargs):
            calls["search_type"] = search_type
            calls["search_kwargs"] = search_kwargs
            return SimpleNamespace()  # underlying retriever

    store = PGVectorEmbeddingStore(FakePGVector())
    ret = store.as_retriever(user_id="u123", extra=99)

    assert isinstance(ret, PGVectorRetriever)

    # check arguments passed to pgvector
    assert calls["search_type"] == "mmr"
    assert calls["search_kwargs"]["filter"] == {"user_id": "u123"}
    assert calls["search_kwargs"]["extra"] == 99
    assert calls["search_kwargs"]["k"] == 8
    assert calls["search_kwargs"]["fetch_k"] == 24
