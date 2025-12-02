from datetime import date
from types import SimpleNamespace

import pytest

from app.schemas.shopping_list import (
    ShoppingListItemRead,
    ShoppingListRead,
)
from app.services.shopping_list_service import ShoppingListService

#
# -----------------------
#   Fakes
# -----------------------
#


class FakeDB:
    """Simulates SQLAlchemy .execute()."""

    def __init__(self, recipes=None, meal_plans=None):
        # recipes and meal_plans must be dict id -> object
        self.recipes = recipes or {}
        self.meal_plans = meal_plans or {}
        self.last_query = None

    async def execute(self, query):
        """Return a FakeResult with scalars()."""
        self.last_query = query

        # detect whether the query is for Recipe or MealPlan
        if "recipe" in str(query).lower():
            # Must return an object with .scalars() → iterator of stored Recipe objects
            return FakeResult(self.recipes.values())

        if "meal_plan" in str(query).lower():
            return FakeResult(self.meal_plans.values())

        return FakeResult([])


class FakeResult:
    """Mimics SQLAlchemy Result with scalars()."""

    def __init__(self, objs):
        self._objs = list(objs)

    def scalars(self):
        return iter(self._objs)


class FakeRepo:
    """Fake ShoppingListRepository with shopping list and DB handle."""

    def __init__(self, shopping_list, db):
        self._shopping_list = shopping_list
        self.db = db
        self.get_called = False

    async def get_shopping_list(self, user_id):
        self.get_called = True
        return self._shopping_list


#
# -----------------------
#   Helper constructors
# -----------------------
#


def make_item(
    *,
    item_id,
    ingredient,
    checked=False,
    recipe_id=None,
    note=None,
    meal_plan_id=None,
    meal_plan_day=None,
    meal_type=None,
):
    """Return a fake ORM object with attributes compatible with ShoppingListItemRead."""
    return SimpleNamespace(
        id=item_id,
        ingredient_name=ingredient,
        quantity=None,
        unit=None,
        recipe_title=None,
        checked=checked,
        recipe_id=recipe_id,
        note=note,
        meal_plan_id=meal_plan_id,
        meal_plan_day=meal_plan_day,
        meal_type=meal_type,
    )


def make_recipe(id, title):
    return SimpleNamespace(id=id, title=title)


def make_meal_plan(id, start, end):
    return SimpleNamespace(id=id, start_date=start, end_date=end)


#
# -----------------------
#   Tests
# -----------------------
#


@pytest.mark.asyncio
async def test_shopping_list_basic_recipe_grouping():
    """
    Ensures:
    - items become ShoppingListItemRead models
    - recipe groups produce ImportedRecipe entries
    """
    item1 = make_item(item_id="i1", ingredient="Tomato", recipe_id="r1")
    item2 = make_item(item_id="i2", ingredient="Salt", recipe_id="r1")
    shopping_list = SimpleNamespace(items=[item1, item2])

    fake_db = FakeDB(recipes={"r1": make_recipe("r1", "Tomato Soup")})
    repo = FakeRepo(shopping_list, fake_db)

    service = ShoppingListService(repo)
    out: ShoppingListRead = await service.get_shopping_list_read("user1")

    # Items parsed
    assert len(out.items) == 2
    assert isinstance(out.items[0], ShoppingListItemRead)

    # Imported recipes grouped
    assert len(out.imported_recipes) == 1
    assert out.imported_recipes[0].recipe_id == "r1"
    assert out.imported_recipes[0].title == "Tomato Soup"


@pytest.mark.asyncio
async def test_shopping_list_unknown_recipe_title():
    """
    If recipe_id exists in items but not in DB query results,
    title → 'Unknown Recipe'.
    """
    item = make_item(item_id="i1", ingredient="Carrot", recipe_id="missing")
    shopping_list = SimpleNamespace(items=[item])

    fake_db = FakeDB(recipes={})  # no recipe returned
    repo = FakeRepo(shopping_list, fake_db)

    service = ShoppingListService(repo)
    out = await service.get_shopping_list_read("u1")

    assert len(out.imported_recipes) == 1
    assert out.imported_recipes[0].recipe_id == "missing"
    assert out.imported_recipes[0].title == "Unknown Recipe"


@pytest.mark.asyncio
async def test_shopping_list_meal_plan_grouping():
    """
    Ensures that meal plans are grouped and formatted correctly.
    """
    # Two items from same meal plan
    item1 = make_item(
        item_id="i1",
        ingredient="Chicken",
        meal_plan_id="mp1",
        meal_plan_day=date(2024, 5, 1),
        meal_type="dinner",
    )
    item2 = make_item(
        item_id="i2",
        ingredient="Garlic",
        meal_plan_id="mp1",
        meal_plan_day=date(2024, 5, 1),
        meal_type="dinner",
    )

    shopping_list = SimpleNamespace(items=[item1, item2])

    fake_plan = make_meal_plan("mp1", start=date(2024, 5, 1), end=date(2024, 5, 7))
    fake_db = FakeDB(meal_plans={"mp1": fake_plan})
    repo = FakeRepo(shopping_list, fake_db)

    service = ShoppingListService(repo)
    out = await service.get_shopping_list_read("u1")

    assert len(out.imported_meal_plans) == 1
    mp = out.imported_meal_plans[0]

    assert mp.meal_plan_id == "mp1"
    assert mp.name.startswith("Week of May")  # formatted correctly


@pytest.mark.asyncio
async def test_shopping_list_multiple_groups():
    """
    Tests mixture of:
    - recipe groups
    - meal plan groups
    - unrelated items
    """
    items = [
        make_item(item_id="i1", ingredient="Tomato", recipe_id="r1"),
        make_item(item_id="i2", ingredient="Salt"),
        make_item(
            item_id="i3",
            ingredient="Pepper",
            meal_plan_id="mp1",
            meal_plan_day=date(2024, 5, 2),
            meal_type="lunch",
        ),
    ]

    shopping_list = SimpleNamespace(items=items)

    fake_db = FakeDB(
        recipes={"r1": make_recipe("r1", "Tomato Soup")},
        meal_plans={"mp1": make_meal_plan("mp1", date(2024, 5, 2), date(2024, 5, 8))},
    )
    repo = FakeRepo(shopping_list, fake_db)

    service = ShoppingListService(repo)
    out = await service.get_shopping_list_read("user")

    # Items count
    assert len(out.items) == 3

    # One recipe imported
    assert len(out.imported_recipes) == 1
    assert out.imported_recipes[0].recipe_id == "r1"

    # One meal plan imported
    assert len(out.imported_meal_plans) == 1
    assert out.imported_meal_plans[0].meal_plan_id == "mp1"


@pytest.mark.asyncio
async def test_shopping_list_no_recipes_no_meal_plans():
    """
    Ensures empty groups handled correctly.
    """
    item = make_item(item_id="i1", ingredient="Bread")
    shopping_list = SimpleNamespace(items=[item])

    fake_db = FakeDB(recipes={}, meal_plans={})
    repo = FakeRepo(shopping_list, fake_db)

    service = ShoppingListService(repo)
    out = await service.get_shopping_list_read("u1")

    assert out.imported_recipes == []
    assert out.imported_meal_plans == []
    assert len(out.items) == 1
