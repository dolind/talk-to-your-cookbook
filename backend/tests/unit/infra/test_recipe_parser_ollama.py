import asyncio
import sys
import types
from pathlib import Path

from app.infra.recipe_parser_ollama import OllamaParser, ensure_ollama_model

BASE_DIR = Path(__file__).resolve().parents[3]
sys.path.append(str(BASE_DIR / "backend"))

pydantic_module = sys.modules.setdefault("pydantic", types.ModuleType("pydantic"))
if not hasattr(pydantic_module, "BaseModel"):

    class BaseModel:
        @classmethod
        def model_json_schema(cls):
            return {}

    def Field(*args, **kwargs):
        return None

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class ConfigDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    pydantic_module.BaseModel = BaseModel
    pydantic_module.Field = Field
    pydantic_module.field_validator = field_validator
    pydantic_module.ConfigDict = ConfigDict

httpx_module = sys.modules.setdefault("httpx", types.ModuleType("httpx"))
if not hasattr(httpx_module, "AsyncClient"):
    httpx_module.AsyncClient = None


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.raise_called = False

    def json(self):
        return self._payload

    def raise_for_status(self):
        self.raise_called = True


class FakeAsyncClient:
    def __init__(self, get_response=None, post_response=None, post_calls=None):
        self.get_response = get_response
        self.post_response = post_response
        self.post_calls = post_calls if post_calls is not None else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        return self.get_response

    async def post(self, url, json):
        self.post_calls.append((url, json))
        return self.post_response


def fake_client_factory(get_response=None, post_response=None, post_calls=None):
    def _factory(*args, **kwargs):
        return FakeAsyncClient(get_response, post_response, post_calls)

    return _factory


def test_ensure_ollama_model_pulls_missing_model(monkeypatch):
    post_calls = []
    tags_response = FakeResponse({"models": [{"name": "other"}]})
    pull_response = FakeResponse({})
    monkeypatch.setattr(
        "app.infra.recipe_parser_ollama.httpx.AsyncClient",
        fake_client_factory(tags_response, pull_response, post_calls),
    )

    asyncio.run(ensure_ollama_model("target", "http://ollama"))

    assert post_calls == [("http://ollama/api/pull", {"name": "target"})]


def test_ensure_ollama_model_skips_when_present(monkeypatch):
    post_calls = []
    tags_response = FakeResponse({"models": [{"name": "target"}]})
    monkeypatch.setattr(
        "app.infra.recipe_parser_ollama.httpx.AsyncClient",
        fake_client_factory(tags_response, post_response=None, post_calls=post_calls),
    )

    asyncio.run(ensure_ollama_model("target", "http://ollama"))

    assert post_calls == []


def test_call_model_sends_prompt_and_returns_content(monkeypatch):
    post_calls = []
    response_payload = {"message": {"content": {"title": "Soup"}}}
    response = FakeResponse(response_payload)
    monkeypatch.setattr(
        "app.infra.recipe_parser_ollama.httpx.AsyncClient",
        fake_client_factory(post_response=response, post_calls=post_calls),
    )

    class OutputType:
        @staticmethod
        def model_json_schema():
            return {"type": "object"}

    parser = OllamaParser(base_url="http://ollama/", model="llama")

    result = asyncio.run(
        parser.call_model(
            input_text="recipe text",
            instruction="parse this",
            output_type=OutputType,
        )
    )

    assert post_calls == [
        (
            "http://ollama/api/chat",
            {
                "model": "llama",
                "messages": [
                    {"role": "system", "content": "parse this"},
                    {"role": "user", "content": "recipe text"},
                ],
                "format": {"type": "object"},
                "temperature": 0.2,
                "stream": False,
            },
        )
    ]
    assert response.raise_called is True
    assert result == {"title": "Soup"}
