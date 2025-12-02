from __future__ import annotations

import base64
import itertools
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence

from fastapi import HTTPException, UploadFile
from sqlalchemy import Text, cast, delete, func, nulls_last, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.recipe import Recipe, RecipeIngredient, RecipeInstruction, RecipeNutrition
from app.ports.storage import StorageService
from app.schemas.recipe import RecipeCreate, RecipeSearchParams, RecipeUpdate

FULL_LOAD = (
    selectinload(Recipe.ingredients),
    selectinload(Recipe.instructions),
    selectinload(Recipe.nutrition),
)


def _attach_children(rec: Recipe, src: RecipeCreate | RecipeUpdate) -> None:
    if src.ingredients:
        rec.ingredients = [RecipeIngredient(order=i, **ing.model_dump()) for i, ing in enumerate(src.ingredients)]
    if src.instructions:
        rec.instructions = [
            RecipeInstruction(step=i + 1, instruction=getattr(instr, "instruction", instr))
            for i, instr in enumerate(src.instructions)
        ]
    if src.nutrition:
        rec.nutrition = RecipeNutrition(
            calories=src.nutrition.calories,
            protein=src.nutrition.protein,
            carbohydrates=src.nutrition.carbohydrates,
            fat=src.nutrition.fat,
            fiber=src.nutrition.fiber,
            sugar=src.nutrition.sugar,
            sodium=src.nutrition.sodium,
            additional_data=json.dumps(src.nutrition.additional_data) if src.nutrition.additional_data else None,
        )


def _get_sort_column(sort: str):
    return {
        "name": Recipe.title.asc(),
        "rating": nulls_last(Recipe.rating.desc()),
        "recent": Recipe.created_at.desc(),
    }.get(sort, Recipe.created_at.desc())


def _add_json_array_filter(query, column, values, dialect):
    if not values:
        return query
    if dialect.startswith("sqlite"):
        for v in values:
            pattern = f'%"{v}"%'
            query = query.filter(cast(column, Text).like(pattern))
    else:
        query = query.filter(or_(*[cast(column, JSONB).contains([v]) for v in values]))
    return query


async def _save_upload(rid: str, file: UploadFile, storage: StorageService) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{rid}_{uuid.uuid4()}{ext}"
    await storage.save_image(file, filename, kind="recipe")
    return filename


async def _delete_image_file(filename: str, storage: StorageService) -> None:
    await storage.delete(filename, kind="recipe")


class RecipeRepository:
    model = Recipe

    def __init__(self, db: AsyncSession):
        self.db = db

    # ────────────────── Internal Helpers ──────────────────
    def _base(self, *, owner_id: str | None = None):
        stmt = select(self.model).options(*FULL_LOAD)
        if owner_id:
            stmt = stmt.where(self.model.user_id == owner_id)
        return stmt

    async def _count(self, stmt):
        return await self.db.scalar(select(func.count()).select_from(stmt.subquery()))

    async def _one(self, stmt):
        return (await self.db.execute(stmt)).scalar_one()

    async def _one_or_none(self, stmt):
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _must_get_owned(self, rid: str, owner_id: str) -> Recipe:
        rec = await self._one_or_none(self._base().where(Recipe.id == rid))
        if not rec:
            raise HTTPException(404, "Recipe not found")
        if rec.user_id != owner_id:
            raise HTTPException(403, "Not allowed")
        return rec

    # small helper to safely get dialect name
    def _dialect_name(self) -> str:
        # AsyncSession.bind can be None; get_bind() will resolve the engine/bind
        try:
            bind = self.db.bind or self.db.get_bind()
            return bind.dialect.name if bind else "sqlite"
        except Exception:
            # be conservative; tests run on sqlite by default
            return "sqlite"

    # ────────────────── CRUD Methods ──────────────────
    async def add(
        self,
        recipe_in: RecipeCreate,
        owner_id: str,
        file: UploadFile | None = None,
        storage: StorageService | None = None,
    ) -> Recipe:
        rec = Recipe(
            user_id=owner_id,
            title=recipe_in.title,
            description=recipe_in.description,
            prep_time=recipe_in.prep_time,
            cook_time=recipe_in.cook_time,
            servings=recipe_in.servings,
            image_url=recipe_in.image_url,
            rating=recipe_in.rating,
            source=recipe_in.source,
            source_url=recipe_in.source_url,
            categories=recipe_in.categories if recipe_in.categories else None,
            tags=recipe_in.tags if recipe_in.tags else None,
        )
        _attach_children(rec, recipe_in)
        self.db.add(rec)
        await self.db.flush()

        if file:
            img_name = await _save_upload(rec.id, file, storage)
            rec.image_url = img_name

            # OPTIONAL: support base64 from JSON
        elif recipe_in.image_url and recipe_in.image_url.startswith("data:image/"):
            header, b64 = recipe_in.image_url.split(",", 1)
            ext = header.split("/")[1].split(";")[0]
            filename = f"{rec.id}.{ext}"
            raw = base64.b64decode(b64)
            await storage.save_binary_image(raw, filename, kind="recipe")
            rec.image_url = filename

        await self.db.commit()

        return await self._one(self._base().where(self.model.id == rec.id))

    async def get(self, id_: str, *, owner_id: str) -> Recipe | None:
        return await self._one_or_none(self._base(owner_id=owner_id).where(self.model.id == id_))

    async def update(
        self,
        recipe_id: str,
        owner_id: str,
        patch: RecipeUpdate,
        file: UploadFile | None = None,
        delete_image: bool = False,
        storage: StorageService = None,
    ) -> Recipe:
        rec = await self._must_get_owned(recipe_id, owner_id)
        for field in self.SCALAR_FIELDS:
            if (val := getattr(patch, field, None)) is not None:
                setattr(rec, field, val)

        if patch.categories is not None:
            rec.categories = patch.categories
        if patch.tags is not None:
            rec.tags = patch.tags

        if delete_image and rec.image_url:
            await _delete_image_file(rec.image_url, storage)
            rec.image_url = None

        if file:
            new_name = await _save_upload(recipe_id, file, storage)
            if rec.image_url:
                await _delete_image_file(str(rec.image_url), storage)
            rec.image_url = new_name

        if patch.ingredients is not None:
            await self.db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == rec.id))
            rec.ingredients = [
                RecipeIngredient(recipe_id=rec.id, order=i, **ing.model_dump())
                for i, ing in enumerate(patch.ingredients)
            ]

        if patch.instructions is not None:
            await self.db.execute(delete(RecipeInstruction).where(RecipeInstruction.recipe_id == rec.id))
            rec.instructions = [
                RecipeInstruction(recipe_id=rec.id, step=i + 1, instruction=ins.instruction)
                for i, ins in enumerate(patch.instructions)
            ]

        if patch.nutrition is not None:
            n = rec.nutrition or RecipeNutrition(recipe_id=rec.id)
            for k, v in patch.nutrition.model_dump(exclude_unset=True).items():
                setattr(n, k, json.dumps(v) if k == "additional_data" and v else v)
            rec.nutrition = n

        rec.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return await self._one(self._base().where(Recipe.id == rec.id))

    async def bulk_delete(self, ids: List[str], owner_id: str) -> None:
        stmt = delete(Recipe).where(Recipe.id.in_(ids), Recipe.user_id == owner_id)
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(404, "No recipes found")
        await self.db.commit()

    # ──────────────── Specialized Queries ────────────────
    async def similar(self, embedding: list[float], k: int = 5) -> Sequence[Recipe]:
        stmt = text("SELECT * FROM recipes ORDER BY embedding <=> :emb LIMIT :k").bindparams(emb=embedding, k=k)
        return (await self.db.execute(stmt)).scalars().all()

    async def infinite_scroll(
        self,
        *,
        owner_id: str,
        page: int,
        page_size: int,
        sort: str = "recent",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        max_time: Optional[int] = None,
        search: Optional[str] = None,
    ) -> dict:
        skip = (page - 1) * page_size
        sort_column = _get_sort_column(sort)
        query = self._base(owner_id=owner_id)

        dialect = self._dialect_name()

        if search:
            term = f"%{search}%"
            query = query.filter(or_(Recipe.title.ilike(term), Recipe.description.ilike(term)))
        if categories:
            query = _add_json_array_filter(query, Recipe.categories, categories, dialect)
        if tags:
            query = _add_json_array_filter(query, Recipe.tags, tags, dialect)
        if source:
            query = query.filter(Recipe.source == source)
        if max_time is not None:
            query = query.filter((Recipe.prep_time + Recipe.cook_time) <= max_time)

        query = query.order_by(sort_column).offset(skip).limit(page_size + 1)

        results = (await self.db.execute(query)).unique().scalars().all()
        return {
            "items": results[:page_size],
            "hasMore": len(results) > page_size,
        }

    async def list(
        self,
        *,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        max_prep_time: int | None = None,
    ):
        stmt = self._base(owner_id=owner_id)
        if search:
            term = f"%{search}%"
            stmt = stmt.filter(or_(Recipe.title.ilike(term), Recipe.description.ilike(term)))
        if category:
            stmt = stmt.filter(Recipe.categories.contains(category))
        if tag:
            stmt = stmt.filter(Recipe.tags.contains(tag))
        if max_prep_time is not None:
            stmt = stmt.filter(Recipe.prep_time <= max_prep_time)

        stmt = stmt.order_by(Recipe.created_at.desc())
        total = await self._count(stmt)
        items = (await self.db.execute(stmt.offset(skip).limit(limit))).scalars().all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get_visible(self, recipe_id: str, viewer_id: str) -> Recipe:
        rec = await self._one_or_none(self._base().where(Recipe.id == recipe_id))
        if not rec:
            raise HTTPException(404, "Recipe not found")
        if rec.user_id != viewer_id and not rec.is_public:
            raise HTTPException(403, "Not allowed")
        return rec

    async def advanced_search(
        self, *, owner_id: str, params: RecipeSearchParams, skip: int, limit: int
    ) -> dict[str, Any]:
        stmt = self._base(owner_id=owner_id)
        if params.search_term:
            term = f"%{params.search_term}%"
            stmt = stmt.filter(or_(Recipe.title.ilike(term), Recipe.description.ilike(term)))

        if params.categories:
            stmt = stmt.filter(or_(*(Recipe.categories.contains(c) for c in params.categories)))
        if params.tags:
            stmt = stmt.filter(or_(*(Recipe.tags.contains(t) for t in params.tags)))
        if params.max_prep_time is not None:
            stmt = stmt.filter(Recipe.prep_time <= params.max_prep_time)

        if params.min_calories is not None or params.max_calories is not None:
            nut = RecipeNutrition
            sub = select(nut.recipe_id)
            if params.min_calories is not None:
                sub = sub.filter(nut.calories >= params.min_calories)
            if params.max_calories is not None:
                sub = sub.filter(nut.calories <= params.max_calories)
            ids = (await self.db.execute(sub)).scalars().all()
            stmt = stmt.filter(Recipe.id.in_(ids))

        order_field = {
            "title": Recipe.title,
            "prep_time": Recipe.prep_time,
        }.get(params.sort_by, Recipe.created_at)
        stmt = stmt.order_by(order_field.asc() if params.sort_asc else order_field.desc())

        total = await self._count(stmt)
        items = (await self.db.execute(stmt.offset(skip).limit(limit))).scalars().all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get_filters(self, *, user_id: str) -> dict:
        source_stmt = select(func.distinct(Recipe.source)).where(Recipe.user_id == user_id)
        sources_result = await self.db.execute(source_stmt)
        sources = [row[0] for row in sources_result if row[0]]

        category_stmt = select(Recipe.categories).where(Recipe.user_id == user_id)
        result = (await self.db.execute(category_stmt)).scalars().all()
        flattened = itertools.chain.from_iterable(
            json.loads(cat) if isinstance(cat, str) else cat or [] for cat in result
        )
        categories = sorted(set(flattened))
        return {"categories": categories, "sources": sources}

    # Static constants
    SCALAR_FIELDS = {
        "title",
        "description",
        "prep_time",
        "cook_time",
        "servings",
        "image_url",
        "source",
        "source_url",
        "is_public",
        "rating",
    }

    async def get_all_ids(self, owner_id: str) -> List[str]:
        result = await self.db.execute(select(self.model.id).where(self.model.user_id == owner_id))
        return [row[0] for row in result.fetchall()]
