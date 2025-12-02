import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import END
from langgraph.graph import StateGraph

from app.repos.recipe import RecipeRepository
from app.schemas.chat import ChatState
from app.schemas.recipe import RecipeRead

logger = logging.getLogger(__name__)


def last_user_text(state: ChatState) -> str:
    for m in reversed(state.messages):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def classify_chat_intent(state: ChatState) -> Literal["specific", "ragchat"]:
    """
    Very simple routing:
    - if a recipe is selected in the session/graph state -> 'specific'
    - else start rag chat
    """
    return "specific" if state.selected_recipe_id else "ragchat"


def _format_recipe_for_prompt(recipe) -> str:
    data = RecipeRead.model_validate(recipe).model_dump(exclude_none=True)
    parts: list[str] = [f"Title: {data['title']}"]

    description = data.get("description")
    if description:
        parts.append(f"\nDescription:\n{description}")

    ingredients = data.get("ingredients")
    if ingredients:
        ing_text = "\n".join(f"- {ing['name']}" for ing in ingredients if ing.get("name"))
        if ing_text:
            parts.append(f"\nIngredients:\n{ing_text}")

    instructions = data.get("instructions")
    if instructions:
        steps = [step.get("instruction") for step in instructions if step.get("instruction")]
        if steps:
            instr_text = "\n".join(f"{i + 1}. {text}" for i, text in enumerate(steps))
            parts.append(f"\nInstructions:\n{instr_text}")

    return "\n\n".join(parts)


async def node_specific_recipe(state: ChatState, config):
    prompt = ChatPromptTemplate.from_template(
        "You are a helpful cooking assistant.\n"
        "Answer ONLY using the provided recipe context.\n\n"
        "Recipe Context:\n{recipe_text}\n\n"
        "User: {question}\n"
    )
    parser = StrOutputParser()
    recipe_repo: RecipeRepository = config["configurable"]["recipe_repo"]
    llm = config["configurable"]["llm"]
    recipe_id = state.selected_recipe_id
    user_id = state.user_id
    if not recipe_id:
        return {"messages": [AIMessage(content="I need a recipe to answer your question.")]}

    recipe = await recipe_repo.get(recipe_id, owner_id=user_id)
    if not recipe:
        logger.warning("Recipe %s not found for user %s", recipe_id, user_id)
        return {"messages": [AIMessage(content="I couldn't find that recipe.")]}

    recipe_text = _format_recipe_for_prompt(recipe)

    question = last_user_text(state)
    answer = await (prompt | llm | parser).ainvoke({"recipe_text": recipe_text, "question": question})
    return {"messages": [AIMessage(content=answer)]}


def node_ragchat_retrieve(state: ChatState, config):
    q = last_user_text(state)
    retriever = config["configurable"]["retriever"]
    docs = retriever.get_relevant_documents(q)

    if not docs:
        rag_context = "NO_MATCH"
    else:
        parts = [f"- [{d['metadata']['title']}](http://recipe?{d['metadata']['recipe_id']})" for d in docs[:8]]
        rag_context = "\n".join(parts)
    return {"messages": [SystemMessage(content=f"RETRIEVED_CONTEXT:\n{rag_context}")]}


async def node_ragchat_answer(state: ChatState, config):
    q = last_user_text(state)
    llm = config["configurable"]["llm"]

    # Find the latest SystemMessage that starts with RETRIEVED_CONTEXT
    retrieved = ""

    for m in reversed(state.messages):
        if isinstance(m, SystemMessage) and m.content.startswith("RETRIEVED_CONTEXT:"):
            retrieved = m.content.replace("RETRIEVED_CONTEXT:", "", 1).strip()
            break
    logger.info(f"Retrieved {retrieved}")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "MODE:RAG_ANSWER"),
            ("system", "You are a helpful cooking assistant."),
            ("system", "Use ONLY the RETRIEVED_CONTEXT below to suggest options and answer."),
            ("system", "Always provide the link that was in the retrieved context. Do not repeat recipe content."),
            (
                "system",
                "If context is NO_MATCH, say you couldn’t find matching recipes and ask a brief clarifying question.",
            ),
            ("system", "RETRIEVED_CONTEXT:\n{retrieved}"),
            ("human", "{question}"),
        ]
    )

    parser = StrOutputParser()

    chain = prompt | llm | parser

    answer = await chain.ainvoke({"retrieved": retrieved, "question": q})
    return {"messages": [AIMessage(content=answer)]}


def route(state: ChatState):
    return state


def build_simple_rag_graph(checkpointer: AsyncPostgresSaver):
    """
    llm: any LC-compatible chat model (e.g., ChatOpenAI, ChatMistral)
    retriever: configured retriever (PGVector.as_retriever) with per-user filters
    load_recipe_text(recipe_id, user_id) -> str : your function to load a full recipe blob
    """
    g = StateGraph(ChatState)

    # Nodes
    g.add_node("specific_answer", node_specific_recipe)
    g.add_node("ragchat_retrieve", node_ragchat_retrieve)
    g.add_node("ragchat_answer", node_ragchat_answer)

    g.add_node("route", route)
    g.set_entry_point("route")

    g.add_conditional_edges(
        "route",
        classify_chat_intent,
        {
            "specific": "specific_answer",
            "ragchat": "ragchat_retrieve",
        },
    )
    g.add_edge("ragchat_retrieve", "ragchat_answer")
    g.add_edge("ragchat_answer", END)
    g.add_edge("specific_answer", END)

    return g.compile(checkpointer=checkpointer)
