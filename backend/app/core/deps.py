import logging
from typing import Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.database.init_db import get_db
from app.experimental.classification_mock import MockClassificationService
from app.experimental.ocr_mock_0 import SuperSimpleOCRMockService
from app.experimental.ocr_mock_1 import MockOCRService
from app.experimental.segmentation_mock import NoSegmentationService
from app.infra.classification_simple import ClassificationSimple
from app.infra.ocr_google import GoogleVisionOCRService
from app.infra.ocr_pytesseract import PytesseractOCRService
from app.infra.recipe_parser_mistral import MistralParser
from app.infra.recipe_parser_ollama import OllamaParser
from app.infra.thumbnail_pillow import PillowThumbnailService
from app.infra.validation_simple import ValidationSimple
from app.models.user import User
from app.ports import thumbnail
from app.ports.classification import ClassificationService
from app.ports.ocr import OCRService, TextOrImageService
from app.ports.segmentation import SegmentationService
from app.ports.storage import StorageService
from app.ports.validation import ValidationService
from app.repos.book import BookScanRepository
from app.repos.classification_record import ClassificationRecordRepository
from app.repos.image_repo import ImageRepository
from app.repos.meal_plan import MealPlanRepository
from app.repos.recipe import RecipeRepository
from app.repos.shopping_list import ShoppingListRepository
from app.repos.user import UserRepository
from app.services.image_ingest_service import ImageIngestService
from app.services.text_or_image_simple import TextOrImageSimple
from app.workflows.queues.queues import QueueRegistry, get_queue_registry

logger = logging.getLogger(__name__)
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


# Pure constructors — for workers, tests, wrappers
def new_book_scan_repo(db: AsyncSession) -> BookScanRepository:
    return BookScanRepository(db)


def new_image_repo(db: AsyncSession) -> ImageRepository:
    return ImageRepository(db)


def new_classification_repo(db: AsyncSession) -> ClassificationRecordRepository:
    return ClassificationRecordRepository(db)


def new_meal_plan_repo(db: AsyncSession) -> MealPlanRepository:
    return MealPlanRepository(db)


def new_recipe_repo(db: AsyncSession) -> RecipeRepository:
    return RecipeRepository(db)


def new_shopping_list_repo(db: AsyncSession) -> ShoppingListRepository:
    return ShoppingListRepository(db)


# for fastapi app


def get_book_repo(db: AsyncSession = Depends(get_db)) -> BookScanRepository:
    return new_book_scan_repo(db)


def get_image_repo(db: AsyncSession = Depends(get_db)) -> ImageRepository:
    return new_image_repo(db)


def get_classification_repo(db: AsyncSession = Depends(get_db)) -> ClassificationRecordRepository:
    return new_classification_repo(db)


def get_meal_plan_repo(db: AsyncSession = Depends(get_db)) -> MealPlanRepository:
    return new_meal_plan_repo(db)


def get_recipe_repo(db: AsyncSession = Depends(get_db)) -> RecipeRepository:
    return new_recipe_repo(db)


def get_shopping_list_repo(db: AsyncSession = Depends(get_db)) -> ShoppingListRepository:
    return new_shopping_list_repo(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except (JWTError, ValidationError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    return user


async def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges")
    return current_user


def get_storage(request: Request) -> StorageService:
    return request.app.state.storage


def make_scoped_repo(repo_factory, session_maker):
    """
    Wraps a repo constructor to return a proxy that opens its own session per call.
    """

    class ScopedRepo:
        def __getattr__(self, name):
            async def wrapper(*args, **kwargs):
                async with session_maker() as session:
                    repo = repo_factory(session)
                    method = getattr(repo, name)
                    return await method(*args, **kwargs)

            return wrapper

    return ScopedRepo()


def get_segmentation_service() -> SegmentationService:
    seg_type = settings.SEGMENTATION.lower()

    if seg_type == "mock":
        return NoSegmentationService()
    return NoSegmentationService()


def get_classification_service() -> ClassificationService:
    provider = settings.LLM_API_PROVIDER

    if provider == "mistralai":
        return ClassificationSimple(
            parser=MistralParser(
                api_key=settings.MISTRAL_API_KEY,
                model=settings.CHAT_MODEL_MISTRAL,
            )
        )
    if provider == "ollama":
        return ClassificationSimple(
            parser=OllamaParser(
                base_url=settings.OLLAMA_URL,
                model=settings.CHAT_MODEL_OLLAMA,
            )
        )

    return MockClassificationService()


def get_ocr_service() -> OCRService:
    backend = settings.OCR_BACKEND.lower()

    if backend == "google":
        return GoogleVisionOCRService(api_key=settings.GOOGLE_API_KEY)

    elif backend == "tesseract":
        return PytesseractOCRService()

    elif backend == "mock":
        return MockOCRService(mock_response_path=settings.MOCK_RESPONSE_FILE)

    elif backend == "supersimple":
        return SuperSimpleOCRMockService()

    else:
        raise ValueError(f"Unsupported OCR backend: {backend}")


_thumbnail_singletons: Dict[str, thumbnail.ThumbnailService] = {}


def get_thumbnail_service() -> thumbnail.ThumbnailService:
    thumbs = settings.THUMBNAIL_TYPE.lower()

    if thumbs not in _thumbnail_singletons:
        if thumbs == "mock":
            _thumbnail_singletons[thumbs] = PillowThumbnailService()
        else:
            raise ValueError(f"Unsupported Thumbnail type: {thumbs}")

    return _thumbnail_singletons[thumbs]


def get_validation_service() -> ValidationService:
    return ValidationSimple()


def get_image_ingest_service(
    db: AsyncSession = Depends(get_db),
    queues: QueueRegistry = Depends(get_queue_registry),
    storage: StorageService = Depends(get_storage),
) -> ImageIngestService:
    """
    Inject an `AsyncSession` into a freshly‑constructed repository.
    """
    return ImageIngestService(storage, get_image_repo(db), queues.ocr)


_text_or_image_singleton = None


def get_text_or_image_service() -> TextOrImageService:
    global _text_or_image_singleton
    if _text_or_image_singleton is None:
        _text_or_image_singleton = TextOrImageSimple()
    return _text_or_image_singleton
