from __future__ import annotations

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.retrievers import BaseRetriever

from app.repos.recipe import RecipeRepository
from app.workflows.recipeassistant.llm_factory import get_llm_from_settings


async def build_graph_config(thread_id: str, user_id: str, recipe_repo: RecipeRepository, rag_retriever: BaseRetriever):
    # LLM (streaming or not depending on endpoint)
    llm = await get_llm_from_settings(
        streaming=True,
        temperature=0.2,
    )

    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user_id),
            "llm": llm,
            "recipe_repo": recipe_repo,
            "retriever": rag_retriever,
        }
    }


class PrintTokens(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs):
        print(token, end="", flush=True)
