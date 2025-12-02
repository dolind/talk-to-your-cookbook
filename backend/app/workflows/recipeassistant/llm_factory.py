import asyncio
import re
from typing import List

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.core.config import get_settings

settings = get_settings()


class MockChatModel(BaseChatModel):
    model: str = "mock"

    @property
    def _llm_type(self) -> str:
        return "mock"

    # ---------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------
    def _parse_prompt(self, messages: List[BaseMessage]):
        # LC compile result → last message is always HumanMessage(prompt)
        raw = messages[-1].content if messages else ""

        # Extract User: question
        user_question = ""
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("User:"):
                user_question = line.replace("User:", "", 1).strip()
                break

        # Extract retrieved context
        retrieved_context = None
        full_prompt = "\n".join(m.content for m in messages)

        if "RETRIEVED_CONTEXT:" in full_prompt:
            retrieved_context = raw.split("RETRIEVED_CONTEXT:", 1)[1].strip()

        return user_question, retrieved_context

    def _build_reply(self, messages: List[BaseMessage]) -> str:
        full_prompt = "\n".join(m.content for m in messages)

        # Extract user question
        user_q = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_q = m.content.strip()
                break

        # --- CASE 1: RAG RETRIEVAL MODE ---
        if "RETRIEVED_CONTEXT:" in full_prompt:
            retrieved = full_prompt.split("RETRIEVED_CONTEXT:", 1)[1].strip()

            if retrieved.startswith("NO_MATCH"):
                return (
                    f"[mock:{self.model}] I looked for matching recipes but found none. "
                    f"You asked: '{user_q}'. Try rephrasing?"
                )
            else:
                return (
                    f"[mock:{self.model}] I found these relevant recipes:\n\n"
                    f"{retrieved}\n\n"
                    f"Your question was: '{user_q}'. Hope this helps!"
                )

        # --- CASE 2: SPECIFIC RECIPE MODE ---
        return f"[mock:{self.model}] Good question! I'm sure you'll figure it out just fine."

    # ---------------------------------------
    # NON-STREAMING
    # ---------------------------------------
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text = self._build_reply(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages)

    # ---------------------------------------
    # STREAMING
    # ---------------------------------------
    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        text = self._build_reply(messages)
        tokens = re.split(r"(\n)", text)

        for tok in tokens:
            chunk = AIMessageChunk(content=tok + " ")
            gen_chunk = ChatGenerationChunk(message=chunk)
            if run_manager:
                run_manager.on_llm_new_token(tok + " ")
            yield gen_chunk

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        text = self._build_reply(messages)
        tokens = re.split(r"(\n)", text)

        for tok in tokens:
            chunk = AIMessageChunk(content=tok + " ")
            gen_chunk = ChatGenerationChunk(message=chunk)
            if run_manager:
                await run_manager.on_llm_new_token(tok + " ")
            yield gen_chunk
            await asyncio.sleep(0.01)


async def get_llm_from_settings(
    streaming: bool = True,
    temperature: float = 0.2,
) -> BaseChatModel:
    """
    Create a chat model using LangChain's init_chat_model.
    provider: "mistralai" | "openai" | "ollama" | "mock"
    """
    provider = settings.LLM_API_PROVIDER.strip().lower()

    if provider == "mock":
        return MockChatModel(model="dev-mock")
    # shared kwargs
    kwargs = {"temperature": temperature, "streaming": streaming}
    # pick model per provider
    if provider == "mistralai":
        model = settings.CHAT_MODEL_MISTRAL
        kwargs["api_key"] = settings.MISTRAL_API_KEY
    elif provider == "ollama":
        model = settings.CHAT_MODEL_OLLAMA
        # await ensure_ollama_model(model=model, base_url=settings.OLLAMA_URL)
        if settings.OLLAMA_URL:
            kwargs["base_url"] = settings.OLLAMA_URL
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    # provider-specific extras
    if provider == "ollama" and settings.OLLAMA_URL:
        kwargs["base_url"] = settings.OLLAMA_URL  # e.g., http://localhost:11434

    # init_chat_model picks up API keys from env automatically:
    # - MISTRAL_API_KEY
    # - OPENAI_API_KEY
    # (Ollama needs only base_url)
    return init_chat_model(model, model_provider=provider, **kwargs)
