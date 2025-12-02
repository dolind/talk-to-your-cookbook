import base64
import datetime
import gzip
import io
import json
import zipfile
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from httpx import AsyncClient
from sqlalchemy import select

from app.core.deps import get_recipe_repo
from app.main import app as fastapi_app
from app.models.recipe import Recipe
from app.routes.recipes import build_mealie_export, build_paprika_export, parse_mealie, parse_paprika
from app.schemas.recipe import (
    RecipeCreate,
    RecipeIngredientCreate,
    RecipeInstructionCreate,
)


@pytest.mark.asyncio
async def test_create_recipe(authed_client_session: AsyncClient):
    recipe_payload = RecipeCreate(
        title="Test Pancakes",
        description="Delicious pancakes",
        prep_time=10,
        cook_time=15,
        servings=2,
        ingredients=[
            RecipeIngredientCreate(
                name="Flour",
                quantity="1",
                unit="cup",
                preparation=None,
            )
        ],
        instructions=[
            RecipeInstructionCreate(step=1, instruction="Mix all ingredients."),
            RecipeInstructionCreate(step=2, instruction="Cook on skillet until golden brown."),
        ],
    )

    form_data = {"data": json.dumps(recipe_payload.model_dump())}  # <-- THIS must be a string

    response = await authed_client_session.post(
        "/api/v1/recipes/",
        data=form_data,
        files={},  # must be present if using File(...) in FastAPI
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Test Pancakes"
    assert data["ingredients"][0]["name"] == "Flour"
    assert len(data["instructions"]) == 2


@pytest.mark.asyncio
async def test_list_recipes(authed_client_session, db_session, test_user):
    db_session.add(Recipe(user_id=test_user.id, title="R1", prep_time=5, cook_time=10, servings=1))
    await db_session.commit()

    response = await authed_client_session.get("/api/v1/recipes/")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_get_recipes_infinite(authed_client_session, db_session, test_user):
    for i in range(3):
        db_session.add(Recipe(user_id=test_user.id, title=f"R{i}", prep_time=5, cook_time=10, servings=1))
    await db_session.commit()

    response = await authed_client_session.get("/api/v1/recipes/infinite?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["hasMore"] is True


@pytest.mark.asyncio
async def test_search_recipes(authed_client_session, db_session, test_user):
    recipe = Recipe(
        user_id=test_user.id, title="Avocado Salad", description="fresh", prep_time=5, cook_time=0, servings=1
    )
    db_session.add(recipe)
    await db_session.commit()

    response = await authed_client_session.post("/api/v1/recipes/search", json={"search_term": "avocado"})
    assert response.status_code == 200

    items = response.json()["items"]
    assert any("avocado" in r["title"].lower() for r in items)


@pytest.mark.asyncio
async def test_get_recipe(authed_client_session, db_session, test_user):
    recipe = Recipe(user_id=test_user.id, title="Test", prep_time=5, cook_time=10, servings=1)
    recipe.is_public = True
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    response = await authed_client_session.get(f"/api/v1/recipes/{recipe.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test"


@pytest.mark.asyncio
async def test_update_recipe(authed_client_session, db_session, test_user):
    recipe = Recipe(
        user_id=test_user.id,
        title="Old",
        prep_time=1,
        cook_time=1,
        servings=1,
        is_public=True,
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    form_data = {"data": json.dumps({"title": "Updated"}), "delete_image": "false"}
    response = await authed_client_session.put(
        f"/api/v1/recipes/{recipe.id}",
        data=form_data,
        files={"file": ("dummy.png", b"", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_bulk_delete_recipes(authed_client_session, db_session, test_user):
    # Create recipes for that user
    r1 = Recipe(user_id=test_user.id, title="To Delete 1", prep_time=1, cook_time=1, servings=1)
    r2 = Recipe(user_id=test_user.id, title="To Delete 2", prep_time=1, cook_time=1, servings=1)
    db_session.add_all([r1, r2])
    await db_session.commit()
    await db_session.refresh(r1)
    await db_session.refresh(r2)

    # Sanity check query
    result = await db_session.execute(
        select(Recipe).where(Recipe.id.in_([r1.id, r2.id]), Recipe.user_id == test_user.id)
    )
    found = result.scalars().all()
    assert len(found) == 2  # ← very important check

    # Request
    body = {"ids": [str(r1.id), str(r2.id)]}
    response = await authed_client_session.request("DELETE", "/api/v1/recipes/bulk-delete", json=body)

    assert response.status_code == 204

    # Confirm deletion
    post_check = await db_session.execute(select(Recipe).where(Recipe.id.in_([r1.id, r2.id])))
    assert len(post_check.scalars().all()) == 0


@pytest.mark.asyncio
async def test_get_filters_api(authed_client_session, db_session, test_user):
    # Create test recipes
    recipes = [
        Recipe(title="Test A", user_id=test_user.id, categories='["Lunch", "Healthy"]', source="Chef Alex"),
        Recipe(title="Test B", user_id=test_user.id, categories='["Lunch", "Quick"]', source="Chef Alex"),
        Recipe(title="Test C", user_id=test_user.id, categories='["Dinner"]', source="Chef Jamie"),
    ]
    db_session.add_all(recipes)
    await db_session.commit()

    # Act: Call the endpoint
    response = await authed_client_session.get("/api/v1/recipes/filters")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["categories"]) == ["Dinner", "Healthy", "Lunch", "Quick"]
    assert sorted(data["sources"]) == ["Chef Alex", "Chef Jamie"]


# ----------------------------------------------------------------------
#  PAPRIKA IMPORT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_paprika(monkeypatch, authed_client_session, test_user):
    """
    Covers import_recipes() logic for .paprikarecipes files:
    - ZIP parsing
    - gzip decompress
    - parsing of ingredients + directions
    - base64 image handling
    """

    # Create paprika-style JSON
    paprika_json = {
        "name": "Paprika Imported",
        "ingredients": "Salt\nPepper",
        "directions": "Mix\nServe",
        "description": "desc",
        "categories": ["Dinner"],
        "tags": ["tag1"],
        "notes": "some note",
        "source": "Paprika",
        "source_url": "http://x",
        "photo_data": base64.b64encode(b"fake_img").decode(),
    }
    raw = gzip.compress(json.dumps(paprika_json).encode())

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as z:
        z.writestr("1.paprikarecipe", raw)

    mem.seek(0)

    # ------------------------------------------------------------------
    # Fake repo.add
    # ------------------------------------------------------------------
    fake_repo = AsyncMock()
    saved_model = type("FakeSaved", (), {"id": "new1"})
    fake_repo.add.return_value = saved_model

    fastapi_app.dependency_overrides[get_recipe_repo] = lambda: fake_repo

    # Actually call endpoint
    files = {"file": ("import.paprikarecipes", mem.getvalue(), "application/octet-stream")}
    res = await authed_client_session.post("/api/v1/recipes/import", files=files)

    assert res.status_code == 201
    payload = res.json()

    assert payload["imported"] == 1
    assert payload["ids"] == ["new1"]

    # Validate parser called expected fields
    call_args = fake_repo.add.call_args[0][0]  # RecipeCreate
    assert call_args.title == "Paprika Imported"
    assert len(call_args.ingredients) == 2
    assert call_args.ingredients[0].name == "Salt"


# ----------------------------------------------------------------------
#  PAPRIKA PARSER UNIT TEST
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_paprika_unit():
    paprika_json = {
        "name": "R1",
        "ingredients": "A\nB",
        "directions": "step1\nstep2",
        "photo_data": base64.b64encode(b"IMGDATA").decode(),
    }
    raw = gzip.compress(json.dumps(paprika_json).encode())

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as z:
        z.writestr("x.paprikarecipe", raw)

    mem.seek(0)

    out = await parse_paprika(mem.getvalue())
    assert len(out) == 1

    recipe_in, img = out[0]
    assert recipe_in.title == "R1"
    assert len(recipe_in.ingredients) == 2
    assert isinstance(img, UploadFile)


# ----------------------------------------------------------------------
#  MEALIE IMPORT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_mealie(monkeypatch, authed_client_session):
    data = [
        {
            "name": "Mealie1",
            "ingredients": [{"note": "Egg"}, {"note": "Milk"}],
            "instructions": [{"text": "Do X"}, {"text": "Do Y"}],
            "image": "data:image/png;base64," + base64.b64encode(b"img").decode(),
        }
    ]

    # Fake recipe repo.save
    fake_repo = AsyncMock()
    fake_repo.add.return_value = type("Saved", (), {"id": "abc"})

    fastapi_app.dependency_overrides[get_recipe_repo] = lambda: fake_repo

    res = await authed_client_session.post(
        "/api/v1/recipes/import",
        files={"file": ("import.json", json.dumps(data).encode(), "application/json")},
    )

    assert res.status_code == 201
    assert res.json()["ids"] == ["abc"]

    call_args = fake_repo.add.call_args[0][0]
    assert call_args.title == "Mealie1"
    assert len(call_args.ingredients) == 2


# ----------------------------------------------------------------------
#  MEALIE PARSER UNIT TEST
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_mealie_unit():
    data = [
        {
            "name": "x",
            "ingredients": [{"note": "A"}],
            "instructions": [{"text": "S"}],
            "image": "data:image/jpeg;base64," + base64.b64encode(b"img").decode(),
        }
    ]

    raw = json.dumps(data).encode()
    parsed = await parse_mealie(raw)

    recipe_in, img = parsed[0]
    assert recipe_in.title == "x"
    assert isinstance(img, UploadFile)


# ----------------------------------------------------------------------
#  PAPRIKA EXPORT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_paprika_export(monkeypatch):
    fake_storage = AsyncMock()
    fake_storage.get_image_path.return_value = "/tmp/img1.jpg"

    # prepare dummy recipe model with minimal required fields
    class FakeIng:
        def __init__(self, name):
            self.name = name

    class FakeInstr:
        def __init__(self, instruction):
            self.instruction = instruction

    class FakeRecipe:
        id = "r1"
        title = "Exported"
        ingredients = [FakeIng("Salt")]
        instructions = [FakeInstr("Mix")]
        notes = "n"
        categories = ["C"]
        tags = ["T"]
        description = "d"
        rating = None
        created_at = datetime.datetime.now()
        image_url = "img1.jpg"

    # Fake local file
    def fake_open(path, mode):
        return io.BytesIO(b"IMAGE")

    monkeypatch.setattr("builtins.open", fake_open)

    out_bytes = await build_paprika_export([FakeRecipe()], fake_storage)

    # Validate ZIP content
    mem = io.BytesIO(out_bytes)
    with zipfile.ZipFile(mem) as z:
        names = z.namelist()
        assert any(name.endswith(".paprikarecipe") for name in names)


# ----------------------------------------------------------------------
#  MEALIE EXPORT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_mealie_export():
    class FakeIng:
        def __init__(self, name):
            self.name = name

    class FakeInstr:
        def __init__(self, instruction):
            self.instruction = instruction

    class FakeRecipe:
        id = "1"
        title = "R"
        description = "d"
        ingredients = [FakeIng("I")]
        instructions = [FakeInstr("S")]
        servings = 2
        tags = ["t"]
        notes = "bla"
        categories = ["C"]
        rating = None

    out = await build_mealie_export([FakeRecipe()], storage=None)

    assert isinstance(out, list)
    assert out[0]["name"] == "R"
    assert out[0]["recipe_servings"] == 2
