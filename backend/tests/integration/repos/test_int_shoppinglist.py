from datetime import date

import pytest
from fastapi import HTTPException

from app.models.meal_plan import MealPlan, MealPlanDay, MealPlanItem, MealType
from app.models.recipe import Recipe, RecipeIngredient
from app.repos.shopping_list import ShoppingListRepository, parse_quantity
from app.schemas.shopping_list import ShoppingListItemCreate, ShoppingListItemUpdate

# ============================================================
# FIXTURE
# ============================================================


@pytest.fixture
def shopping_repo(db_session):
    return ShoppingListRepository(db_session)


# ============================================================
# parse_quantity() tests
# ============================================================


@pytest.mark.parametrize(
    "input_qty, expected",
    [
        ("3", 3.0),
        ("1.5", 1.5),
        ("1/2", 0.5),
        ("abc", None),
        ("1/0", None),
        (None, None),
        (2, 2.0),
        (2.5, 2.5),
    ],
)
def test_parse_quantity_cases(input_qty, expected):
    assert parse_quantity(input_qty) == expected


# ============================================================
# get_shopping_list
# ============================================================


@pytest.mark.asyncio
async def test_get_shopping_list_creates_if_missing(shopping_repo, test_user):
    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert sl
    assert sl.owner_id == test_user.id
    assert sl.name == "My Shopping List"


@pytest.mark.asyncio
async def test_get_shopping_list_returns_existing(shopping_repo, test_user):
    sl1 = await shopping_repo.get_shopping_list(test_user.id)
    sl2 = await shopping_repo.get_shopping_list(test_user.id)
    assert sl1.id == sl2.id


# ============================================================
# add_item
# ============================================================


@pytest.mark.asyncio
async def test_add_item(shopping_repo, test_user):
    item = await shopping_repo.add_item(
        test_user.id,
        ShoppingListItemCreate(ingredient_name="Milk", quantity=1, unit="L"),
    )
    assert item.ingredient_name == "Milk"
    assert item.unit == "L"
    assert item.checked is False


@pytest.mark.asyncio
async def test_add_item_minimal_fields(shopping_repo, test_user):
    item = await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Salt"))
    assert item.unit is None
    assert item.quantity is None
    assert item.checked is False


# ============================================================
# update_item
# ============================================================


@pytest.mark.asyncio
async def test_update_item(shopping_repo, test_user):
    item = await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Eggs"))
    updated = await shopping_repo.update_item(
        test_user.id,
        item.id,
        ShoppingListItemUpdate(checked=True, quantity=6),
    )
    assert updated.checked is True
    assert updated.quantity == 6


@pytest.mark.asyncio
async def test_update_item_partial(shopping_repo, test_user):
    item = await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Egg"))
    updated = await shopping_repo.update_item(test_user.id, item.id, ShoppingListItemUpdate(unit="pcs"))
    assert updated.unit == "pcs"
    assert updated.ingredient_name == "Egg"


@pytest.mark.asyncio
async def test_update_item_set_fields_to_none(shopping_repo, test_user):
    item = await shopping_repo.add_item(
        test_user.id,
        ShoppingListItemCreate(ingredient_name="Butter", quantity=1, unit="g"),
    )
    updated = await shopping_repo.update_item(
        test_user.id,
        item.id,
        ShoppingListItemUpdate(quantity=None, unit=None),
    )
    assert updated.quantity is None
    assert updated.unit is None


@pytest.mark.asyncio
async def test_update_item_not_found(shopping_repo, test_user):
    with pytest.raises(HTTPException) as exc:
        await shopping_repo.update_item(test_user.id, "missing-id", ShoppingListItemUpdate(checked=True))
    assert exc.value.status_code == 404


# ============================================================
# delete_item
# ============================================================


@pytest.mark.asyncio
async def test_delete_item(shopping_repo, test_user):
    item = await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Butter"))
    await shopping_repo.delete_item(test_user.id, item.id)

    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert all(i.id != item.id for i in sl.items)


@pytest.mark.asyncio
async def test_delete_item_nonexistent(shopping_repo, test_user):
    # Should not raise
    await shopping_repo.delete_item(test_user.id, "does-not-exist")


# ============================================================
# clear_shopping_list
# ============================================================


@pytest.mark.asyncio
async def test_clear_shopping_list(shopping_repo, test_user):
    await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Flour"))
    await shopping_repo.clear_shopping_list(test_user.id)
    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert len(sl.items) == 0


# ============================================================
# remove_by_recipe
# ============================================================


@pytest.mark.asyncio
async def test_remove_by_recipe(shopping_repo, test_user):
    await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Salt", recipe_id="r1"))
    await shopping_repo.remove_by_recipe(test_user.id, "r1")

    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert all(i.recipe_id != "r1" for i in sl.items)


@pytest.mark.asyncio
async def test_remove_by_recipe_multiple(shopping_repo, test_user):
    # Both items have recipe_id *in the input*, but add_item() ignores it.
    await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="A", recipe_id="r"))
    await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="B", recipe_id="r"))

    await shopping_repo.remove_by_recipe(test_user.id, "r")
    sl = await shopping_repo.get_shopping_list(test_user.id)

    # Because recipe_id is not stored by add_item(), NOTHING should be deleted.
    assert len(sl.items) == 2
    assert all(i.recipe_id is None for i in sl.items)


# ============================================================
# remove_by_meal_plan
# ============================================================


@pytest.mark.asyncio
async def test_remove_by_meal_plan(shopping_repo, test_user):
    await shopping_repo.add_item(test_user.id, ShoppingListItemCreate(ingredient_name="Tomato", meal_plan_id="plan1"))
    await shopping_repo.remove_by_meal_plan(test_user.id, "plan1")

    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert all(i.meal_plan_id != "plan1" for i in sl.items)


@pytest.mark.asyncio
async def test_remove_by_meal_plan_no_items(shopping_repo, test_user):
    # Should not raise
    await shopping_repo.remove_by_meal_plan(test_user.id, "empty-plan")


# ============================================================
# remove_by_meal_plan_recipe
# ============================================================


@pytest.mark.asyncio
async def test_remove_by_meal_plan_recipe(shopping_repo, test_user):
    await shopping_repo.add_item(
        test_user.id,
        ShoppingListItemCreate(
            ingredient_name="Onion",
            meal_plan_id="plan123",
            meal_plan_day="monday",
            meal_type=MealType.lunch,
            recipe_id="recipe456",
        ),
    )
    await shopping_repo.remove_by_meal_plan_recipe(
        test_user.id,
        meal_plan_id="plan123",
        day="monday",
        meal_type=MealType.lunch,
        recipe_id="recipe456",
    )

    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert all(
        not (
            i.meal_plan_id == "plan123"
            and i.meal_plan_day == "monday"
            and i.meal_type == MealType.lunch
            and i.recipe_id == "recipe456"
        )
        for i in sl.items
    )


@pytest.mark.asyncio
async def test_remove_by_meal_plan_recipe_no_plan(shopping_repo, test_user):
    # Should not raise even if meal plan does not exist
    await shopping_repo.remove_by_meal_plan_recipe(
        test_user.id,
        meal_plan_id="nope",
        day=date.today(),
        meal_type=MealType.dinner,
        recipe_id="xyz",
    )


# ============================================================
# import_recipe
# ============================================================


@pytest.mark.asyncio
async def test_import_recipe(shopping_repo, test_user, db_session):
    recipe = Recipe(id="r789", title="Test", user_id=test_user.id)
    recipe.ingredients = [
        RecipeIngredient(name="Sugar", quantity="2", unit="tbsp", order=1),
        RecipeIngredient(name="Salt", quantity="1/2", unit="tsp", order=2),
    ]

    db_session.add(recipe)
    await db_session.commit()

    await shopping_repo.import_recipe(test_user.id, "r789")

    sl = await shopping_repo.get_shopping_list(test_user.id)
    names = {i.ingredient_name for i in sl.items}
    assert {"Sugar", "Salt"} <= names


@pytest.mark.asyncio
async def test_import_recipe_missing(shopping_repo, test_user):
    with pytest.raises(HTTPException):
        await shopping_repo.import_recipe(test_user.id, "missing-id")


# ============================================================
# import_meal_plan
# ============================================================


@pytest.mark.asyncio
async def test_import_meal_plan(shopping_repo, test_user, db_session):
    # Create recipe
    recipe = Recipe(id="rec001", user_id=test_user.id, title="X")
    ing1 = RecipeIngredient(id="i1", name="Tomato", quantity="2", unit="pcs", recipe_id="rec001", order=1)
    ing2 = RecipeIngredient(id="i2", name="Cheese", quantity="100", unit="g", recipe_id="rec001", order=2)
    db_session.add(recipe)
    db_session.add_all([ing1, ing2])

    # Create meal plan referencing this recipe
    day = MealPlanDay(id="d1", date=date.today())
    item = MealPlanItem(recipe_id="rec001", meal_type=MealType.lunch, notes="Lunch")
    day.items.append(item)

    plan = MealPlan(
        id="plan001",
        user_id=test_user.id,
        name="Test Plan",
        start_date=date.today(),
        end_date=date.today(),
    )
    plan.days.append(day)

    db_session.add(plan)
    await db_session.commit()

    await shopping_repo.import_meal_plan(test_user.id, "plan001")
    sl = await shopping_repo.get_shopping_list(test_user.id)

    names = {i.ingredient_name for i in sl.items}
    assert {"Tomato", "Cheese"} <= names

    for i in sl.items:
        assert i.recipe_id == "rec001"
        assert i.meal_plan_id == "plan001"
        assert i.meal_type == MealType.lunch
        assert i.note == "Lunch"


@pytest.mark.asyncio
async def test_import_meal_plan_not_found(shopping_repo, test_user):
    with pytest.raises(HTTPException):
        await shopping_repo.import_meal_plan(test_user.id, "missing-plan")


@pytest.mark.asyncio
async def test_import_meal_plan_no_recipes(shopping_repo, test_user, db_session):
    # Create meal plan with NO recipe refs
    plan = MealPlan(
        id="empty",
        user_id=test_user.id,
        name="Empty",
        start_date=date.today(),
        end_date=date.today(),
    )
    plan.days.append(MealPlanDay(date=date.today()))
    db_session.add(plan)
    await db_session.commit()

    with pytest.raises(HTTPException):
        await shopping_repo.import_meal_plan(test_user.id, "empty")


@pytest.mark.asyncio
async def test_import_meal_plan_skips_unowned_recipe(shopping_repo, test_user, db_session):
    # recipe NOT owned by user
    other = Recipe(id="other", user_id="someone_else", title="X")
    db_session.add(other)

    # meal plan refers to it
    day = MealPlanDay(date=date.today())
    day.items.append(MealPlanItem(recipe_id="other", meal_type=MealType.breakfast))

    plan = MealPlan(
        id="planx",
        user_id=test_user.id,
        name="Test",
        start_date=date.today(),
        end_date=date.today(),
    )
    plan.days.append(day)
    db_session.add(plan)
    await db_session.commit()

    await shopping_repo.import_meal_plan(test_user.id, "planx")

    sl = await shopping_repo.get_shopping_list(test_user.id)
    assert len(sl.items) == 0  # skipped silently
