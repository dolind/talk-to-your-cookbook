import enum
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.recipe import RecipeCreate


class PageStatus(enum.Enum):
    QUEUED = "QUEUED"
    OCR_DONE = "OCR_DONE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    FAILED = "failed"


class PageType(enum.Enum):
    IMAGE = "image"
    TEXT = "text"


class RecordStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    REVIEW_GROUPING = "REVIEW_GROUPING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NEEDS_TAXONOMY = "NEEDS_TAXONOMY"
    APPROVED = "APPROVED"


class OCRResult(BaseModel):
    page_id: str
    full_text: str
    blocks: List[Dict[str, Any]]


class SegmentationSegment(BaseModel):
    id: int
    title: str
    bounding_boxes: List[List[Dict[str, int]]]
    associated_ocr_blocks: List[int]


# not used for database
class SegmentationResult(BaseModel):
    segmentation_done: bool = False  # means we always take the entire page
    page_segments: Optional[list[SegmentationSegment]] = None  # we will only use this field in the database


class SegmentationApproval(BaseModel):
    approved: bool = True
    segmentation: Optional[SegmentationResult] = None  # contains user-edits


class PageScanCreate(BaseModel):
    filename: str
    bookScanID: str


class PageScanRead(PageScanCreate):
    id: str
    page_number: int
    scanDate: datetime
    ocr_path: Optional[str] = None
    title: Optional[str] = None
    page_segments: Optional[list[SegmentationSegment]] = None
    segmentation_done: Optional[bool] = False
    page_type: Optional[PageType] = None
    status: Optional[PageStatus] = PageStatus.QUEUED


class PageScanUpdate(BaseModel):
    id: str
    filename: Optional[str] = None
    bookScanID: Optional[str] = None
    page_number: Optional[int] = None
    scanDate: datetime = None
    ocr_path: Optional[str] = None
    title: Optional[str] = None
    page_segments: Optional[list[SegmentationSegment]] = None
    segmentation_done: Optional[bool] = False
    status: Optional[PageStatus] = None
    page_type: Optional[PageType] = None


class SegmentationGraphState(BaseModel):
    page_record_id: str
    ocr_result: OCRResult
    segmentation: Optional[SegmentationResult] = None


class ClassificationRecordInputPage(BaseModel):
    original_id: str
    page_number: int
    ocr_path: Optional[str] = None
    title: Optional[str] = None
    segmentation_done: Optional[bool] = False
    relevant_segment: Optional[SegmentationSegment] = None
    page_type: Optional[PageType] = None


class GraphBroadCast(BaseModel):
    type: str
    id: str
    status: PageStatus | RecordStatus


class ClassificationRecordCreate(BaseModel):
    """Incoming payload to create a scan record.
    You can make some fields required here if you want stricter API semantics."""

    book_scan_id: str


class Page(BaseModel):
    id: str
    page_number: Optional[int] = None


class ClassificationRecordUpdate(BaseModel):
    """PATCH payload – all optional."""

    id: str
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: Optional[RecordStatus] = None
    approved: Optional[bool] = None
    text_pages: Optional[List[Page]] = None
    image_pages: Optional[List[Page]] = None

    validation_result: Optional[RecipeCreate] = None


class ClassificationRecordRead(BaseModel):
    id: str
    book_scan_id: str
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: RecordStatus = RecordStatus.QUEUED
    approved: bool = False
    text_pages: List[Page]
    image_pages: List[Page]

    validation_result: Optional[RecipeCreate] = None

    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    @field_validator("validation_result", mode="before")
    @classmethod
    def parse_recipe_create(cls, v):
        if isinstance(v, dict):
            return RecipeCreate(**v)
        return v

    model_config = ConfigDict(from_attributes=True)


class GroupApproval(BaseModel):
    phase: Literal["group"] = "group"
    approved: bool = True
    new_group: Optional[List[Page]] = None  # contains user-edits


class RecipeApproval(BaseModel):
    phase: Literal["recipe"] = "recipe"
    approved: bool = True
    recipe: Optional[RecipeCreate] = None  # contains user-edits


class TaxonomyApproval(BaseModel):
    phase: Literal["taxonomy"] = "taxonomy"
    approved: bool = True
    categories: Optional[List[str]] = None  # contains user-edits
    tags: Optional[List[str]] = None  # contains user-edits
    source: Optional[str] = None


ApprovalBody = Union[RecipeApproval, TaxonomyApproval, GroupApproval]


class ClassificationGraphState(BaseModel):
    # assigned on create
    classification_record_id: Optional[str] = None
    book_scan_id: Optional[str] = None

    # llm and thumbnail input
    text_pages: Optional[List[PageScanRead]] = None
    image_pages: Optional[List[PageScanRead]] = None
    input_pages: Optional[List[ClassificationRecordInputPage]] = None

    # llm and thumbnail output
    llm_candidate: Optional[Dict] = None
    thumbnail_path: Optional[str] = None

    first_pass_validation: bool = False
    # validation output and every subsequent output
    current_recipe_state: Optional[RecipeCreate] = None
    #
    # taxonomy_user_approved: Optional[dict] = None
    #
    #
    # revalidation_error: Optional[str] = None
    # validation_error: Optional[str] = None
    #
    #
    # # validation uses llm and thumbnail output in 1st pass
    # # 2nd pass uses user input
    # recipe_user_approved: Optional[RecipeCreate] = None
    #
    # recipe_user_approved_and_validated: Optional[RecipeCreate] = None
    #
    # # taxonomy
    # taxonomy_suggestion: Optional[dict] = None
    #
    #
    # # taxonomy interrupt
    taxonomy_user_approved: Optional[dict] = None
    # taxonomy_error: Optional[str]= None


class ClassificationGraphPatch(TypedDict, total=False):
    # assigned on create
    classification_record_id: Optional[str]
    book_scan_id: Optional[str]

    # llm and thumbnail input
    text_pages: Optional[List[PageScanRead]]
    image_pages: Optional[List[PageScanRead]]
    input_pages: Optional[List[ClassificationRecordInputPage]]
    # llm and thumbnail output
    llm_candidate: Optional[Dict]
    thumbnail_path: Optional[str]

    first_pass_validation: bool
    # validation uses llm and thumbnail output in 1st pass
    # 2nd pass uses user input
    current_recipe_state: Optional[RecipeCreate]

    taxonomy_user_approved: Optional[dict]


class BookScanCreate(BaseModel):
    title: str


class BookScanUpdate(BaseModel):
    title: Optional[str] = None


class BookScanRead(BookScanCreate):
    id: str
    imageIds: Optional[list[str]] = None


class IngredientOut(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    preparation: Optional[str] = None


class RecipeLLMOut(BaseModel):
    title: str
    description: Optional[str] = None
    ingredients: List[IngredientOut] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[str] = None
    notes: Optional[str] = None


class ApprovedTaxonomyResult(BaseModel):
    approved: bool = True
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
