# import pytest
#
# from app.infra.services.ollama_parser import OllamaParser
# from app.core.services.ports import PageText
#
#
# class DummyResponse:
#     def __init__(self, status_code=200, json_data=None, text=""):
#         self.status_code = status_code
#         self._json = json_data or {}
#         self.text = text
#
#     def json(self):
#         return self._json
#
#
# class DummyClient:
#     def __init__(self, response):
#         self.response = response
#
#     async def __aenter__(self):
#         return self
#
#     async def __aexit__(self, exc_type, exc, tb):
#         pass
#
#     async def post(self, *args, **kwargs):
#         return self.response
#
#
# @pytest.mark.asyncio
# async def test_parse_success(monkeypatch):
#     parser = OllamaParser(model="x")
#     pages = [PageText(page_no=1, text="text")]
#
#     content = '{"title": "T", "ingredients": [], "steps": []}'
#     resp = DummyResponse(200, {"message": {"content": content}})
#
#     monkeypatch.setattr(
#         "app.services.parser.ollama_parser.httpx.AsyncClient",
#         lambda *a, **k: DummyClient(resp),
#     )
#
#     result = await parser.parse(pages)
#     assert result.title == "T"
#
#
# @pytest.mark.asyncio
# async def test_parse_no_content(monkeypatch):
#     parser = OllamaParser(model="x")
#     pages = [PageText(page_no=1, text="text")]
#
#     resp = DummyResponse(200, {"message": {"content": ""}})
#
#     monkeypatch.setattr(
#         "app.services.parser.ollama_parser.httpx.AsyncClient",
#         lambda *a, **k: DummyClient(resp),
#     )
#
#     with pytest.raises(RuntimeError):
#         await parser.parse(pages)
#
#
# def test_postprocess_markdown():
#     from app.core.services import postprocess
#
#     text = '```json\n{"title": "X"}\n```'
#     assert postprocess(text)["title"] == "X"
#
#
# def test_postprocess_bad_json():
#     from app.core.services import postprocess
#
#     with pytest.raises(ValueError):
#         postprocess("{bad}")
#
#
# @pytest.mark.asyncio
# async def test_parse_api_error(monkeypatch):
#     parser = OllamaParser(model="x")
#     pages = [PageText(page_no=1, text="text")]
#
#     resp = DummyResponse(500, text="fail")
#
#     monkeypatch.setattr(
#         "app.services.parser.ollama_parser.httpx.AsyncClient",
#         lambda *a, **k: DummyClient(resp),
#     )
#
#     with pytest.raises(RuntimeError):
#         await parser.parse(pages)
