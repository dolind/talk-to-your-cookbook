import base64
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.repos.recipe import RecipeRepository
from app.schemas.recipe import (
    RecipeCreate,
    RecipeIngredientCreate,
    RecipeIngredientUpdate,
    RecipeInstructionCreate,
    RecipeInstructionUpdate,
    RecipeNutritionUpdate,
    RecipeSearchParams,
    RecipeUpdate,
)


# ───────────────────────── helpers ──────────────────────────
@pytest.fixture
def recipe_repo(db_session):
    return RecipeRepository(db_session)


def _sample_recipe_create() -> RecipeCreate:
    return RecipeCreate(
        title="Repo Pie",
        description="Test pie",
        prep_time=5,
        cook_time=10,
        servings=1,
        ingredients=[
            RecipeIngredientCreate(name="Flour", quantity="1", unit="cup"),
            RecipeIngredientCreate(name="Sugar", quantity="0.5", unit="cup"),
        ],
        instructions=[
            RecipeInstructionCreate(step=1, instruction="Mix"),
            RecipeInstructionCreate(step=2, instruction="Bake"),
        ],
    )


# ───────────────────────── tests ────────────────────────────
@pytest.mark.asyncio
async def test_add_and_get(recipe_repo, test_user):
    created = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    assert created.id
    assert created.title == "Repo Pie"
    assert len(created.ingredients) == 2
    assert len(created.instructions) == 2

    fetched = await recipe_repo.get(created.id, owner_id=test_user.id)
    assert fetched.title == "Repo Pie"


@pytest.mark.asyncio
async def test_infinite_scroll_basic_pagination(recipe_repo, test_user):
    for i in range(5):
        rc = _sample_recipe_create()
        rc.title = f"R{i}"
        await recipe_repo.add(rc, owner_id=test_user.id)

    page1 = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=1, page_size=2)
    assert len(page1["items"]) == 2
    assert page1["hasMore"] is True

    page2 = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=2, page_size=2)
    assert len(page2["items"]) == 2
    assert page2["hasMore"] is True

    page3 = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=3, page_size=2)
    assert len(page3["items"]) == 1
    assert page3["hasMore"] is False


def _sample(title, categories=None, tags=None):
    return RecipeCreate(
        title=title,
        ingredients=[RecipeIngredientCreate(name="x", quantity="1", unit="u")],
        instructions=[RecipeInstructionCreate(step=1, instruction="mix")],
        categories=categories or [],
        tags=tags or [],
    )


@pytest.mark.asyncio
async def test_infinite_scroll_with_category_filter(recipe_repo, test_user):
    await recipe_repo.add(_sample("Chicken Dinner", categories=["Dinner"]), owner_id=test_user.id)
    await recipe_repo.add(_sample("Eggs", categories=["Breakfast"]), owner_id=test_user.id)

    res = await recipe_repo.infinite_scroll(
        owner_id=test_user.id,
        page=1,
        page_size=10,
        categories=["Dinner"],
    )

    titles = [r.title for r in res["items"]]
    assert "Chicken Dinner" in titles
    assert "Eggs" not in titles
    assert res["hasMore"] is False


@pytest.mark.asyncio
async def test_infinite_scroll_with_tag_filter(recipe_repo, test_user):
    await recipe_repo.add(_sample("My Fav", tags=["Favourite"]), owner_id=test_user.id)
    await recipe_repo.add(_sample("Shopping List", tags=["ToBuy"]), owner_id=test_user.id)

    res = await recipe_repo.infinite_scroll(
        owner_id=test_user.id,
        page=1,
        page_size=10,
        tags=["Favourite"],
    )

    titles = [r.title for r in res["items"]]
    assert "My Fav" in titles
    assert "Shopping List" not in titles
    assert res["hasMore"] is False


@pytest.mark.asyncio
async def test_infinite_scroll_with_search_filter(recipe_repo, test_user):
    rc1 = _sample_recipe_create()
    rc1.title = "Lemon Tart"
    rc1.description = "A sweet lemon dessert"
    await recipe_repo.add(rc1, owner_id=test_user.id)

    rc2 = _sample_recipe_create()
    rc2.title = "Savory Pie"
    rc2.description = "No orange here"
    await recipe_repo.add(rc2, owner_id=test_user.id)

    results = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=1, page_size=10, search="lemon")
    titles = [r.title for r in results["items"]]
    assert "Lemon Tart" in titles
    assert "Savory Pie" not in titles


@pytest.mark.asyncio
async def test_infinite_scroll_with_max_time_filter(recipe_repo, test_user):
    rc1 = _sample_recipe_create()
    rc1.title = "Quick Meal"
    rc1.prep_time = 5
    rc1.cook_time = 10
    await recipe_repo.add(rc1, owner_id=test_user.id)

    rc2 = _sample_recipe_create()
    rc2.title = "Slow Meal"
    rc2.prep_time = 30
    rc2.cook_time = 60
    await recipe_repo.add(rc2, owner_id=test_user.id)

    results = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=1, page_size=10, max_time=20)
    titles = [r.title for r in results["items"]]
    assert "Quick Meal" in titles
    assert "Slow Meal" not in titles


@pytest.mark.asyncio
async def test_infinite_scroll_with_source_filter(recipe_repo, test_user):
    rc1 = _sample_recipe_create()
    rc1.title = "Book Recipe"
    rc1.source = "Cookbook"
    await recipe_repo.add(rc1, owner_id=test_user.id)

    rc2 = _sample_recipe_create()
    rc2.title = "Internet Recipe"
    rc2.source = "Website"
    await recipe_repo.add(rc2, owner_id=test_user.id)

    results = await recipe_repo.infinite_scroll(owner_id=test_user.id, page=1, page_size=10, source="Cookbook")
    titles = [r.title for r in results["items"]]
    assert "Book Recipe" in titles
    assert "Internet Recipe" not in titles


@pytest.mark.asyncio
async def test_list_filter_and_search(recipe_repo, test_user):
    rc1 = _sample_recipe_create()
    rc1.title = "Avocado Toast"
    rc1.description = "fresh"
    await recipe_repo.add(rc1, owner_id=test_user.id)

    rc2 = _sample_recipe_create()
    rc2.title = "Plain Toast"
    await recipe_repo.add(rc2, owner_id=test_user.id)

    res = await recipe_repo.list(owner_id=test_user.id, search="avocado")
    assert len(res["items"]) == 1
    assert res["items"][0].title == "Avocado Toast"


@pytest.mark.asyncio
async def test_get_visible_permissions(user_factory, recipe_repo, test_user):
    viewer = await user_factory()

    private_recipe = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    # Owner can see it
    assert await recipe_repo.get_visible(private_recipe.id, viewer_id=test_user.id)

    # Non-owner can’t
    with pytest.raises(HTTPException):
        await recipe_repo.get_visible(private_recipe.id, viewer_id=viewer.id)

    # Make it public
    private_recipe.is_public = True

    # Now viewer can see
    assert await recipe_repo.get_visible(private_recipe.id, viewer_id=viewer.id)


@pytest.mark.asyncio
async def test_update_title_and_ingredients(recipe_repo, test_user):
    recipe = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    patch = RecipeUpdate(
        title="Updated Pie",
        ingredients=[RecipeIngredientUpdate(name="Butter", quantity="2", unit="tbsp")],
        instructions=[RecipeInstructionUpdate(step=1, instruction="Just mix")],
    )

    updated = await recipe_repo.update(
        recipe_id=recipe.id,
        owner_id=test_user.id,
        patch=patch,
        file=None,
        delete_image=False,
    )
    assert updated.title == "Updated Pie"
    assert len(updated.ingredients) == 1
    assert updated.ingredients[0].name == "Butter"


@pytest.mark.asyncio
async def test_bulk_delete(recipe_repo, test_user):
    r1 = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)
    r2 = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    await recipe_repo.bulk_delete([r1.id, r2.id], owner_id=test_user.id)

    # ensure gone
    remaining = await recipe_repo.list(owner_id=test_user.id)
    assert remaining["total"] == 0


@pytest.mark.asyncio
async def test_advanced_search(recipe_repo, test_user):
    # low-cal and high-cal recipes
    low = _sample_recipe_create()
    low.title = "Light"
    low.nutrition = RecipeNutritionUpdate(calories=100)
    await recipe_repo.add(low, owner_id=test_user.id)

    high = _sample_recipe_create()
    high.title = "Heavy"
    high.nutrition = RecipeNutritionUpdate(calories=800)
    await recipe_repo.add(high, owner_id=test_user.id)

    params = RecipeSearchParams(search_term="", min_calories=200, max_calories=900)
    res = await recipe_repo.advanced_search(owner_id=test_user.id, params=params, skip=0, limit=10)
    titles = [r.title for r in res["items"]]
    assert "Heavy" in titles and "Light" not in titles


@pytest.mark.asyncio
async def test_get_filters_from_repo(recipe_repo, test_user):
    await recipe_repo.add(
        RecipeCreate(
            title="A",
            categories=["Dinner", "Vegetarian"],
            source="User Submitted",
        ),
        owner_id=test_user.id,
    )

    await recipe_repo.add(
        RecipeCreate(
            title="B",
            categories=["Breakfast", "Vegan"],
            source="Official",
        ),
        owner_id=test_user.id,
    )

    await recipe_repo.add(
        RecipeCreate(
            title="C",
            categories=["Dinner"],
            source="User Submitted",
        ),
        owner_id=test_user.id,
    )

    filters = await recipe_repo.get_filters(user_id=test_user.id)

    assert sorted(filters["categories"]) == ["Breakfast", "Dinner", "Vegan", "Vegetarian"]
    assert sorted(filters["sources"]) == ["Official", "User Submitted"]


@pytest.mark.asyncio
async def test_repo_filters_empty(recipe_repo, test_user):
    filters = await recipe_repo.get_filters(user_id=test_user.id)
    assert filters == {"categories": [], "sources": []}


class FakeStorage:
    def __init__(self):
        self.saved = []
        self.deleted = []

    async def save_image(self, file, filename, kind):
        self.saved.append(("image", filename, file.filename))
        return filename

    async def save_binary_image(self, data, filename, kind):
        self.saved.append(("binary", filename, len(data)))
        return filename

    async def delete(self, filename, kind):
        self.deleted.append(filename)


@pytest.mark.asyncio
async def test_add_base64_image(recipe_repo, test_user):
    storage = FakeStorage()

    # fake tiny base64 image
    dummy = base64.b64encode(b"hello").decode()
    b64 = f"data:image/png;base64,{dummy}"

    rc = _sample_recipe_create()
    rc.image_url = b64

    created = await recipe_repo.add(rc, owner_id=test_user.id, storage=storage)

    # saved via save_binary_image
    assert storage.saved
    kind, filename, size = storage.saved[0]
    assert kind == "binary"
    assert filename.startswith(created.id)
    assert size == 5  # "hello"
    assert created.image_url == filename


@pytest.mark.asyncio
async def test_add_with_file_upload(recipe_repo, test_user):
    storage = FakeStorage()
    fake_file = UploadFile(filename="x.png", file=BytesIO(b"abc"))

    created = await recipe_repo.add(
        _sample_recipe_create(),
        owner_id=test_user.id,
        file=fake_file,
        storage=storage,
    )

    assert storage.saved
    kind, filename, original = storage.saved[0]
    assert kind == "image"
    assert original == "x.png"
    assert created.image_url == filename


@pytest.mark.asyncio
async def test_update_delete_image(recipe_repo, test_user):
    storage = FakeStorage()

    fake = UploadFile(filename="old.png", file=BytesIO(b"xx"))
    created = await recipe_repo.add(
        _sample_recipe_create(),
        owner_id=test_user.id,
        file=fake,
        storage=storage,
    )

    old_filename = created.image_url  # store BEFORE update
    storage.saved.clear()

    patch = RecipeUpdate()
    updated = await recipe_repo.update(
        recipe_id=created.id,
        owner_id=test_user.id,
        patch=patch,
        delete_image=True,
        storage=storage,
    )

    assert updated.image_url is None
    assert storage.deleted == [old_filename]


@pytest.mark.asyncio
async def test_update_new_file_replaces_old(recipe_repo, test_user):
    storage = FakeStorage()

    fake = UploadFile(filename="a.png", file=BytesIO(b"aa"))
    created = await recipe_repo.add(_sample_recipe_create(), test_user.id, file=fake, storage=storage)

    old = created.image_url
    storage.saved.clear()

    new_file = UploadFile(filename="b.png", file=BytesIO(b"bb"))
    updated = await recipe_repo.update(
        recipe_id=created.id,
        owner_id=test_user.id,
        patch=RecipeUpdate(),
        file=new_file,
        storage=storage,
    )

    assert storage.deleted == [old]
    assert updated.image_url != old
    assert updated.image_url in {s[1] for s in storage.saved}


@pytest.mark.asyncio
async def test_update_nutrition(recipe_repo, test_user):
    r = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    patch = RecipeUpdate(nutrition=RecipeNutritionUpdate(calories=123, protein=7))

    updated = await recipe_repo.update(
        recipe_id=r.id,
        owner_id=test_user.id,
        patch=patch,
    )

    assert updated.nutrition.calories == 123
    assert updated.nutrition.protein == 7


@pytest.mark.asyncio
async def test_update_categories_and_tags(recipe_repo, test_user):
    r = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    patch = RecipeUpdate(
        categories=["A", "B"],
        tags=["X", "Y"],
    )

    updated = await recipe_repo.update(
        recipe_id=r.id,
        owner_id=test_user.id,
        patch=patch,
    )

    assert updated.categories == ["A", "B"]
    assert updated.tags == ["X", "Y"]


@pytest.mark.asyncio
async def test_update_scalar_fields(recipe_repo, test_user):
    r = await recipe_repo.add(_sample_recipe_create(), owner_id=test_user.id)

    patch = RecipeUpdate(
        title="NewTitle",
        description="NewDesc",
        prep_time=99,
        cook_time=100,
        servings=3,
        source="Book",
        source_url="http://x.com",
    )

    updated = await recipe_repo.update(r.id, test_user.id, patch)
    assert updated.title == "NewTitle"
    assert updated.description == "NewDesc"
    assert updated.prep_time == 99
    assert updated.cook_time == 100
    assert updated.servings == 3
    assert updated.source == "Book"
    assert updated.source_url == "http://x.com"


@pytest.mark.asyncio
async def test_update_not_owned_raises(recipe_repo, user_factory):
    owner = await user_factory()
    other = await user_factory()

    r = await recipe_repo.add(_sample_recipe_create(), owner.id)

    with pytest.raises(HTTPException) as ex:
        await recipe_repo.update(r.id, other.id, RecipeUpdate(title="X"))

    assert ex.value.status_code == 403


@pytest.mark.asyncio
async def test_get_visible_not_found(recipe_repo, test_user):
    with pytest.raises(HTTPException) as ex:
        await recipe_repo.get_visible("no-such-id", viewer_id=test_user.id)
    assert ex.value.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_wrong_owner_raises(recipe_repo, user_factory):
    owner = await user_factory()
    other = await user_factory()

    r = await recipe_repo.add(_sample_recipe_create(), owner.id)

    with pytest.raises(HTTPException) as ex:
        await recipe_repo.bulk_delete([r.id], other.id)

    assert ex.value.status_code == 404


@pytest.mark.asyncio
async def test_list_category_filter(recipe_repo, test_user):
    r1 = _sample_recipe_create()
    r1.categories = ["Dinner"]
    r1 = await recipe_repo.add(r1, test_user.id)

    r2 = _sample_recipe_create()
    r2.categories = ["Breakfast"]
    await recipe_repo.add(r2, test_user.id)

    res = await recipe_repo.list(owner_id=test_user.id, category="Dinner")
    assert [i.id for i in res["items"]] == [r1.id]


@pytest.mark.asyncio
async def test_list_tag_filter(recipe_repo, test_user):
    r1 = _sample_recipe_create()
    r1.tags = ["Fav"]
    r1 = await recipe_repo.add(r1, test_user.id)

    r2 = _sample_recipe_create()
    r2.tags = ["Other"]
    await recipe_repo.add(r2, test_user.id)

    res = await recipe_repo.list(owner_id=test_user.id, tag="Fav")
    assert [i.id for i in res["items"]] == [r1.id]


@pytest.mark.asyncio
async def test_list_max_prep_time(recipe_repo, test_user):
    fast = _sample_recipe_create()
    fast.prep_time = 5
    fast = await recipe_repo.add(fast, test_user.id)

    slow = _sample_recipe_create()
    slow.prep_time = 30
    await recipe_repo.add(slow, test_user.id)

    res = await recipe_repo.list(owner_id=test_user.id, max_prep_time=10)
    assert [i.id for i in res["items"]] == [fast.id]


@pytest.mark.asyncio
async def test_similar_sqlite_raises(recipe_repo, test_user):
    # On sqlite, pgvector operator <=> is invalid → OperationalError
    with pytest.raises(Exception) as e:
        await recipe_repo.similar([0.1, 0.2, 0.3], k=3)


@pytest.mark.asyncio
async def test_get_all_ids(recipe_repo, test_user):
    r1 = await recipe_repo.add(_sample_recipe_create(), test_user.id)
    r2 = await recipe_repo.add(_sample_recipe_create(), test_user.id)

    ids = await recipe_repo.get_all_ids(test_user.id)
    assert set(ids) == {r1.id, r2.id}
