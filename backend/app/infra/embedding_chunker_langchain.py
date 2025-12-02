from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ports.chunker import IChunker


class RecursiveChunker(IChunker):
    def __init__(self, size: int = 800, overlap: int = 100):
        self._s = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)

    def split(self, text: str) -> list[str]:
        return self._s.split_text(text)
