from datetime import datetime
from types import SimpleNamespace

import pytest

from app.models.recipe import Recipe, RecipeIngredient, RecipeInstruction
from app.ports.chunker import IChunker
from app.ports.embedding_store import IEmbeddingStore, RecipeDocs
from app.services.embedding_service import EmbeddingService, recipe_to_text

# ---------------------------------------------------
# Fake dependencies
# ---------------------------------------------------


class FakeRecipeRepo:
    def __init__(self, recipe):
        self.recipe = recipe
        self.calls = []

    async def get(self, recipe_id, owner_id):
        self.calls.append((recipe_id, owner_id))
        return self.recipe


class FakeChunker(IChunker):
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def split(self, text: str):
        self.calls.append(text)
        return self.chunks


class FakeStore(IEmbeddingStore):
    def __init__(self):
        self.add_calls = []
        self.delete_calls = []

    def add(self, docs: RecipeDocs):
        self.add_calls.append(docs)

    def delete(self, ids):
        self.delete_calls.append(ids)

    def as_retriever(self, user_id: str, **kwargs):
        self.retriever_calls.append((user_id, kwargs))
        return SimpleNamespace()


# ---------------------------------------------------
# Helper factory to build ORM objects without DB
# ---------------------------------------------------


def make_recipe_full():
    r = Recipe(
        id="r1",
        user_id="u1",
        title="Tomato Soup",
        description="A warm soup",
        categories=[],
        tags=[],
        created_at=datetime.utcnow(),
    )

    r.ingredients = [
        RecipeIngredient(id="i1", recipe=r, recipe_id="r1", order=1, name="Tomatoes"),
        RecipeIngredient(id="i2", recipe=r, recipe_id="r1", order=2, name="Salt"),
    ]

    r.instructions = [
        RecipeInstruction(id="st1", recipe=r, recipe_id="r1", step=1, instruction="Chop tomatoes."),
        RecipeInstruction(id="st2", recipe=r, recipe_id="r1", step=2, instruction="Boil water."),
    ]

    return r


# ---------------------------------------------------
# recipe_to_text() tests
# ---------------------------------------------------


def test_recipe_to_text_title_only():
    r = Recipe(id="1", user_id="u", title="Just a Title", categories=[], tags=[], created_at=datetime.utcnow())
    r.ingredients = []
    r.instructions = []

    txt = recipe_to_text(r)

    assert "Title: Just a Title" in txt
    assert "Ingredients" not in txt
    assert "Instructions" not in txt


def test_recipe_to_text_full_recipe():
    r = make_recipe_full()

    txt = recipe_to_text(r)

    assert "Title: Tomato Soup" in txt
    assert "Description:\nA warm soup" in txt
    assert "- Tomatoes" in txt
    assert "- Salt" in txt
    assert "1. Chop tomatoes." in txt
    assert "2. Boil water." in txt


# ---------------------------------------------------
# _build_docs() tests
# ---------------------------------------------------


@pytest.mark.asyncio
async def test_build_docs_from_recipe():
    recipe = make_recipe_full()
    repo = FakeRecipeRepo(recipe)
    chunker = FakeChunker(["chunk A", "chunk B"])

    svc = EmbeddingService(repo, chunker)
    docs = await svc._build_docs("r1", "u1")

    # Repo called
    assert repo.calls == [("r1", "u1")]

    # Chunker called with full text
    assert len(chunker.calls) == 1
    full_text = chunker.calls[0]
    assert "Tomatoes" in full_text
    assert "Chop tomatoes." in full_text

    # Docs structure correct
    assert docs.texts == ["chunk A", "chunk B"]
    assert docs.ids == ["r1:0", "r1:1"]
    assert docs.metas[0]["recipe_id"] == "r1"
    assert docs.metas[0]["user_id"] == "u1"
    assert docs.metas[0]["title"] == "Tomato Soup"
    assert docs.metas[0]["chunk_idx"] == 0


# ---------------------------------------------------
# index() tests
# ---------------------------------------------------


@pytest.mark.asyncio
async def test_index_adds_chunks_to_store():
    recipe = make_recipe_full()
    repo = FakeRecipeRepo(recipe)
    chunker = FakeChunker(["A", "B", "C"])
    store = FakeStore()

    svc = EmbeddingService(repo, chunker)
    n = await svc.index(store, recipe_id="r1", user_id="u1", reindex=False)

    assert n == 3
    assert len(store.add_calls) == 1
    assert len(store.delete_calls) == 0


@pytest.mark.asyncio
async def test_index_reindex_deletes_then_adds():
    recipe = make_recipe_full()
    repo = FakeRecipeRepo(recipe)
    chunker = FakeChunker(["C1", "C2"])
    store = FakeStore()

    svc = EmbeddingService(repo, chunker)
    n = await svc.index(store, "r1", "u1", reindex=True)

    # Should delete old IDs
    assert store.delete_calls == [["r1:0", "r1:1"]]

    # Should add new docs
    assert len(store.add_calls) == 1
    assert n == 2


@pytest.mark.asyncio
async def test_index_returns_zero_if_no_recipe():
    repo = FakeRecipeRepo(None)  # repo.get returns None
    chunker = FakeChunker([])
    store = FakeStore()

    svc = EmbeddingService(repo, chunker)
    n = await svc.index(store, recipe_id="X", user_id="U", reindex=False)

    assert n == 0
    assert store.add_calls == []
    assert store.delete_calls == []
