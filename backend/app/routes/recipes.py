import base64
import gzip
import io
import json
import logging
import zipfile
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from starlette.responses import JSONResponse, Response

from app.core.deps import get_current_user, get_recipe_repo, get_storage
from app.models.user import User
from app.ports.storage import StorageService
from app.repos.recipe import RecipeRepository
from app.schemas.recipe import (
    RecipeCreate,
    RecipeDeleteRequest,
    RecipeFilterOptions,
    RecipeIngredientCreate,
    RecipeInstructionCreate,
    RecipePage,
    RecipeRead,
    RecipeSearchParams,
    RecipeUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_update_payload_create(data: str | None, body: RecipeCreate | None) -> RecipeCreate:
    if data:
        try:
            parsed = json.loads(data)
            if not parsed.get("title"):
                raise HTTPException(400, detail="Missing 'title' in recipe data")
            return RecipeCreate(**parsed)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as e:
            raise HTTPException(400, detail="Invalid JSON in recipe data") from e

    if body:
        return body

    raise HTTPException(400, detail="Missing recipe data")


def parse_update_payload_update(data: str | None, body: RecipeUpdate | None) -> RecipeUpdate:
    if data:
        try:
            parsed = json.loads(data)
            return RecipeUpdate(**parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail="Invalid JSON in recipe data") from e

    if body:
        return body

    return RecipeUpdate()


@router.post("/", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    data: str | None = Form(None),  # form: data = JSON stringified RecipeCreate
    recipe_in_body: RecipeCreate | None = Body(None),  # fallback if not multipart
    file: UploadFile | None = File(None),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    storage: StorageService = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    """Create a new recipe."""

    recipe_in = parse_update_payload_create(data, recipe_in_body)
    # Delegate to repository/service

    saved = await recipe_repo.add(recipe_in, owner_id=current_user.id, file=file, storage=storage)
    return saved


# ───────────────────────────────────────────────────────────────
@router.get("/infinite", response_model=RecipePage)
async def get_recipes_infinite(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = "recent",
    categories: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None),
    source: Optional[str] = None,
    max_time: Optional[int] = None,
    search: Optional[str] = None,
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    result = await recipe_repo.infinite_scroll(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        sort=sort,
        categories=categories,
        tags=tags,
        source=source,
        max_time=max_time,
        search=search,
    )
    return result


@router.get("/filters", response_model=RecipeFilterOptions)
async def get_available_filters(
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    filters = await recipe_repo.get_filters(user_id=current_user.id)

    return filters


# ───────────────────────────────────────────────────────────────
@router.get("/", response_model=RecipePage)
async def get_recipes(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    max_prep_time: int | None = None,
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    return await recipe_repo.list(
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        tag=tag,
        max_prep_time=max_prep_time,
    )


# ───────────────────────────────────────────────────────────────
@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: str,
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    return await recipe_repo.get_visible(recipe_id, viewer_id=current_user.id)


# ───────────────────────────────────────────────────────────────
@router.put("/{recipe_id}", response_model=RecipeRead)
async def update_recipe(
    recipe_id: str,
    data: str | None = Form(None),
    file: UploadFile | None = File(None),
    delete_image: bool = Form(False),
    recipe_in_body: RecipeUpdate | None = Body(None),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
):

    recipe_in = parse_update_payload_update(data, recipe_in_body)
    return await recipe_repo.update(
        recipe_id, owner_id=current_user.id, patch=recipe_in, file=file, delete_image=delete_image, storage=storage
    )


# ───────────────────────────────────────────────────────────────
@router.delete("/bulk-delete", status_code=204)
async def bulk_delete_recipes(
    request: RecipeDeleteRequest,
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    await recipe_repo.bulk_delete(request.ids, owner_id=current_user.id)


@router.delete("/recipes", status_code=204)
async def delete_all_recipes(
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    ids = await recipe_repo.get_all_ids(owner_id=current_user.id)
    await recipe_repo.bulk_delete(ids, owner_id=current_user.id)


# ───────────────────────────────────────────────────────────────
@router.post("/search", response_model=RecipePage)
async def search_recipes(
    search_params: RecipeSearchParams = Body(...),
    skip: int = 0,
    limit: int = 100,
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
):
    return await recipe_repo.advanced_search(
        owner_id=current_user.id,
        params=search_params,
        skip=skip,
        limit=limit,
    )


@router.get("/export/paprika")
async def export_paprika(
    current_user=Depends(get_current_user),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    storage=Depends(get_storage),
):
    recipes = await recipe_repo.list(owner_id=current_user.id, skip=0, limit=9999)
    archive_bytes = await build_paprika_export(recipes["items"], storage)
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=recipes.paprikarecipes"},
    )


@router.get("/export/mealie")
async def export_mealie(
    current_user=Depends(get_current_user),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    storage=Depends(get_storage),
):
    recipes = await recipe_repo.list(owner_id=current_user.id, skip=0, limit=9999)
    mealie_json = await build_mealie_export(recipes["items"], storage)
    return JSONResponse(mealie_json)


@router.post("/import", status_code=201)
async def import_recipes(
    file: UploadFile = File(...),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    storage: StorageService = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):

    raw = await file.read()

    # Decide format
    if file.filename.endswith(".paprikarecipes"):

        items = await parse_paprika(raw)
    else:
        items = await parse_mealie(raw)

    # items is List[ (RecipeCreate, UploadFile|None) ]
    imported_ids = []

    for recipe_in, image_file in items:
        saved = await recipe_repo.add(
            recipe_in,
            owner_id=current_user.id,
            file=image_file,
            storage=storage,
        )
        imported_ids.append(saved.id)

    return {"imported": len(imported_ids), "ids": imported_ids}


async def parse_paprika(raw_zip: bytes):
    import base64
    import gzip
    import json
    import zipfile
    from io import BytesIO

    z = zipfile.ZipFile(BytesIO(raw_zip))
    out = []

    for name in z.namelist():
        if not name.endswith(".paprikarecipe"):
            continue

        decompressed = json.loads(gzip.decompress(z.read(name)))

        ingredients = [
            RecipeIngredientCreate(name=line)
            for line in decompressed.get("ingredients", "").splitlines()
            if line.strip()
        ]

        instructions = [
            RecipeInstructionCreate(step=idx + 1, instruction=line)
            for idx, line in enumerate(decompressed.get("directions", "").splitlines())
            if line.strip()
        ]

        recipe_in = RecipeCreate(
            title=decompressed.get("name") or "Untitled",
            description=decompressed.get("description"),
            servings=None,
            categories=_ensure_list(decompressed.get("categories")) or [],
            tags=_ensure_list(decompressed.get("tags")) or [],
            rating=decompressed.get("rating"),
            notes=decompressed.get("notes"),
            source=decompressed.get("source"),
            source_url=decompressed.get("source_url"),
            ingredients=ingredients,
            instructions=instructions,
        )

        # Image handling
        img_file = None
        if decompressed.get("photo_data"):
            # Convert base64 => UploadFile
            img_bytes = base64.b64decode(decompressed["photo_data"])
            img_file = UploadFile(filename="import.jpg", file=BytesIO(img_bytes))

        out.append((recipe_in, img_file))

    return out


def _ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            v = json.loads(value)
            if isinstance(v, list):
                return v
        except Exception:
            pass
    return []


async def parse_mealie(raw_json: bytes):
    import base64
    import json
    from io import BytesIO

    data = json.loads(raw_json)
    if isinstance(data, dict):
        data = [data]

    out = []

    for r in data:
        ingredients = [RecipeIngredientCreate(name=i.get("note", "")) for i in r.get("ingredients", [])]

        instructions = [
            RecipeInstructionCreate(step=idx + 1, instruction=i.get("text", ""))
            for idx, i in enumerate(r.get("instructions", []))
        ]
        recipe_in = RecipeCreate(
            title=r.get("name") or "Untitled",
            description=r.get("description"),
            servings=r.get("recipe_servings"),
            categories=r.get("categories") or [],
            tags=r.get("tags") or [],
            ingredients=ingredients,
            instructions=instructions,
        )

        # Image: Mealie may use data URLs
        img_file = None
        img = r.get("image")

        if img and img.startswith("data:image/"):
            header, b64 = img.split(",", 1)
            ext = header.split("/")[1].split(";")[0]
            img_bytes = base64.b64decode(b64)

            img_file = UploadFile(filename=f"import.{ext}", file=BytesIO(img_bytes))

        out.append((recipe_in, img_file))

    return out


async def build_paprika_export(recipes, storage: StorageService):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as z:
        for r in recipes:
            try:
                image_path = ""
                if r.image_url:
                    image_path = await storage.get_image_path(r.image_url[:-4])
                data = {
                    "name": r.title,
                    "ingredients": "\n".join(i.name for i in r.ingredients),
                    "directions": "\n".join(i.instruction for i in r.instructions),
                    "notes": r.notes,
                    "categories": r.categories or [],
                    "tags": r.tags or [],
                    "description": r.description,
                    "rating": r.rating,
                    "photo_data": base64.b64encode(open(image_path, "rb").read()).decode() if r.image_url else "",
                    "created": r.created_at.isoformat(),
                }
                raw = json.dumps(data).encode()
                compressed = gzip.compress(raw)
                z.writestr(f"{r.id}.paprikarecipe", compressed)
            except Exception as e:
                logger.info(f"Failed to export recipe {r.id}: {e}")
    return mem.getvalue()


async def build_mealie_export(recipes, storage: StorageService):
    out = []
    for r in recipes:
        out.append(
            {
                "name": r.title,
                "description": r.description or "",
                "tags": r.tags or [],
                "notes": r.notes,
                "categories": r.categories or [],
                "recipe_yield": "",
                "rating": r.rating,
                "recipe_servings": r.servings,
                "ingredients": [{"note": i.name} for i in r.ingredients],
                "instructions": [{"text": ins.instruction} for ins in r.instructions],
                "extras": [],
            }
        )
    return out
