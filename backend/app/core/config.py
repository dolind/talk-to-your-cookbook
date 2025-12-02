import os
from functools import lru_cache
from importlib.metadata import metadata
from pathlib import Path
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.embeddings import TargetConfig

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = os.environ.get("APP_ENV_FILE", str(BASE_DIR / ".env.dev"))
m = metadata("talk-to-your-cookbook-backend")


class Settings(BaseSettings):
    # Load either .env.dev or .env.prod
    model_config = SettingsConfigDict(
        env_file=(ENV_FILE,), env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    ENV: str = "dev"

    # Project information
    PROJECT_NAME: str = m["Name"]
    PROJECT_DESCRIPTION: str = m["Summary"]
    PROJECT_VERSION: str = m["Version"]

    # API
    API_V1_STR: str = "/api/v1"

    # DB
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "admin123"
    POSTGRES_DB: str = "mydb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def async_db_url(self) -> str:
        """Build asyncpg URL automatically based on env vars."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_db_url(self) -> str:
        # psycopg (sync) for LangGraph saver
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def pgvector_dsn(self) -> str:
        # LangChain PGVector expects +psycopg
        return self.sync_db_url.replace("postgresql://", "postgresql+psycopg://")

    SERVER_IP: str = "127.0.0.1"
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        f"http://{SERVER_IP}:3000",
        f"http://{SERVER_IP}:5173",
        f"http://{SERVER_IP}:8000",
    ]

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changethissecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 60

    # Files
    THUMBNAIL_TYPE: str = "mock"
    LOCAL_STORAGE_PATH: str = ""

    # OCR
    OCR_BACKEND: str = "supersimple"  # mock, google, supersimple
    GOOGLE_API_KEY: Optional[str] = None
    MOCK_RESPONSE_FILE: str = "tests/unit/data/google_vision_response.json"
    SEGMENTATION: str = "mock"

    # Chat settings
    LLM_API_PROVIDER: str = "mock"  # mock, ollama, mistralai

    CHAT_MODEL_MISTRAL: str = "mistral-large-latest"
    MISTRAL_API_KEY: str = "nothing"

    CHAT_MODEL_OPENAI: str = "gpt-40"
    OPENAI_API_KEY: str = "nothing"

    OLLAMA_URL: Optional[str] = "http://localhost:11434"
    CHAT_MODEL_OLLAMA: str = "mistral:7b-instruct-q4_0"

    EMBEDDING_MODELS: dict = {
        "local_bge": {
            "display_name": "bge-small-en-v1_5",
            "dimensions": 384,
            "provider": "ollama",
            "model_name": "BAAI/bge-small-en-v1.5",  # from EMBEDDING_MODEL_OLLAMA
        },
        "mistralai": {
            "display_name": "mistral-embed",
            "dimensions": 1024,
            "provider": "mistralai",
            "model_name": "mistral-embed",  # from EMBEDDING_MODEL_MISTRAL
        },
        "openai": {
            "display_name": "text-embedding-ada-002",
            "dimensions": 1536,
            "provider": "openai",
            "model_name": "text-embedding-ada-002",  # from EMBEDDING_MODEL_OPENAI
        },
    }

    EMB_TARGETS: str = "local_bge,mistralai,openai"

    EMB_ACTIVE_VERSION: str = "v1"
    EMB_STAGED_VERSION: str = "v1"

    EMB_RAG_ACTIVE: str = "local_bge"

    # Embeddings
    def collection_name(self, target: str, version: str) -> str:
        """
        Generates a consistent PGVector collection name based on an embedding target + version.
        Example: recipes__bge-small-en-v1_5__384__v1

        We currently only support embeddings for recipes, but might add meal plans later.
        """
        if target not in self.EMBEDDING_MODELS:
            raise ValueError(f"Unknown embedding target: {target}")

        model = self.EMBEDDING_MODELS[target]
        return f"recipes__{model['display_name']}__{model['dimensions']}__{version}"

    # produce an EmbeddingsConfig view from env strings
    @property
    def target_config_list(self) -> Dict[str, TargetConfig]:
        config: Dict[str, TargetConfig] = {}
        for t in [x.strip() for x in self.EMB_TARGETS.split(",") if x.strip()]:
            key = t.replace("-", "_").replace(".", "_").upper()
            act = getattr(self, f"EMB_{key}_ACTIVE", None) or self.EMB_ACTIVE_VERSION
            stg = getattr(self, f"EMB_{key}_STAGED", None) or self.EMB_STAGED_VERSION
            config[t] = TargetConfig(target=t, active_version=act, staged_version=stg)
        return config


@lru_cache
def get_settings() -> Settings:
    return Settings()
