from app.models.recipe import Recipe
from app.ports.chunker import IChunker
from app.ports.embedding_store import IEmbeddingStore, RecipeDocs
from app.repos.recipe import RecipeRepository
from app.schemas.recipe import RecipeRead


def recipe_to_text(r: Recipe) -> str:
    data = RecipeRead.model_validate(r).model_dump(exclude_none=True)
    # Build text elegantly
    parts = [f"Title: {data['title']}"]

    if "description" in data:
        parts.append(f"\nDescription:\n{data['description']}")

    if "ingredients" in data and data["ingredients"]:
        ing_text = "\n".join(f"- {ing['name']}" for ing in data["ingredients"])
        parts.append(f"\nIngredients:\n{ing_text}")

    if "instructions" in data and data["instructions"]:
        instr_text = "\n".join(f"{i + 1}. {step['instruction']}" for i, step in enumerate(data["instructions"]))
        parts.append(f"\nInstructions:\n{instr_text}")

    return "\n\n".join(parts)


class EmbeddingService:
    """
    Stores a single recipe as chunks in a vector store.
    """

    def __init__(self, repo: RecipeRepository, chunker: IChunker):
        self.repo = repo
        self.chunker = chunker

    async def _build_docs(self, recipe_id: str, user_id: str) -> RecipeDocs | None:
        r = await self.repo.get(recipe_id, owner_id=user_id)
        if r is None:
            return None
        text = recipe_to_text(r)

        chunks = self.chunker.split(text)

        result = RecipeDocs([], [], [])
        for i, c in enumerate(chunks):
            result.add(
                text=c,
                meta={"recipe_id": r.id, "user_id": r.user_id, "chunk_idx": i, "title": r.title},
                doc_id=f"{r.id}:{i}",
            )

        return result

    async def index(self, store: IEmbeddingStore, recipe_id: str, user_id: str, reindex: bool) -> int:
        """Convert a recipe to chunks and store them. Deletes for reindex=True.
        Returns the number of chunks stored.
        Using the embedding store in the method interface allows us to test different
        embedding stores at runtime with one service.
        """
        recipe_doc_chunks = await self._build_docs(recipe_id, user_id)
        if not recipe_doc_chunks:
            return 0
        if reindex:
            store.delete(recipe_doc_chunks.ids)

        store.add(recipe_doc_chunks)
        return len(recipe_doc_chunks.texts)
