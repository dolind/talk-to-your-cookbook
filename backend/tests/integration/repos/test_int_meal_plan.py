from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.meal_plan import MealPlan, MealPlanItem, MealType
from app.models.recipe import Recipe, RecipeIngredient
from app.repos.meal_plan import MealPlanRepository
from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanDayCreate,
    MealPlanDayUpdate,
    MealPlanItemCreate,
    MealPlanItemUpdate,
    MealPlanUpdate,
)


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------
@pytest.fixture
def meal_repo(db_session):
    return MealPlanRepository(db_session)


@pytest.fixture
def test_recipe(db_session, test_user):
    async def _recipe(title="Dish"):
        rec = Recipe(
            user_id=test_user.id,
            title=title,
            prep_time=5,
            cook_time=10,
            servings=1,
            categories=[],
        )
        db_session.add(rec)
        await db_session.commit()
        await db_session.refresh(rec)
        return rec

    return _recipe


def _plan_create(rec) -> MealPlanCreate:
    return MealPlanCreate(
        name="Weekly Plan",
        description="test",
        start_date=date.today(),
        end_date=date.today(),
        days=[
            MealPlanDayCreate(
                date=date.today(),
                notes="day-1",
                items=[
                    MealPlanItemCreate(
                        recipe_id=rec.id,
                        meal_type=MealType.breakfast,
                        servings=1,
                        notes="yummy",
                    )
                ],
            )
        ],
    )


# =========================================================
#                 Initial Set of Tests
# =========================================================


@pytest.mark.asyncio
async def test_add_and_get(meal_repo, test_recipe, test_user):
    rec = await test_recipe()

    meal = MealPlanCreate(
        name="Plan A",
        description="simple",
        start_date=date.today(),
        end_date=date.today(),
    )
    d = MealPlanDayCreate(date=date.today())
    d.items.append(MealPlanItemCreate(recipe_id=rec.id, meal_type=MealType.breakfast))
    meal.days.append(d)

    saved = await meal_repo.add(test_user.id, meal)
    assert saved.id

    fetched = await meal_repo.get(saved.id, owner_id=test_user.id)
    assert fetched.name == "Plan A"
    assert len(fetched.days) == 1
    assert fetched.days[0].items[0].recipe_id == rec.id


@pytest.mark.asyncio
async def test_update(test_recipe, test_user, meal_repo):
    rec1 = await test_recipe(title="First")
    rec2 = await test_recipe(title="Second")

    plan = MealPlanCreate(name="Orig", start_date=date.today(), end_date=date.today())
    d = MealPlanDayCreate(date=date.today())
    d.items.append(MealPlanItemCreate(recipe_id=rec1.id, meal_type=MealType.lunch))
    plan.days.append(d)

    plan = await meal_repo.add(test_user.id, plan)

    # mutate in memory (OPTION A — expected behavior)
    plan.days[0].items = [MealPlanItem(recipe_id=rec2.id, meal_type=MealType.dinner, servings=2)]

    patch = MealPlanUpdate(name="Updated")  # days = None
    updated = await meal_repo.update(plan.id, test_user.id, patch)

    assert updated.name == "Updated"
    assert updated.days[0].items[0].recipe_id == rec2.id


@pytest.mark.asyncio
async def test_owner_guard(user_factory, test_user, meal_repo, test_recipe):
    intruder = await user_factory()
    await test_recipe()

    plan = MealPlanCreate(
        name="Private",
        start_date=date.today(),
        end_date=date.today(),
    )
    plan.days.append(MealPlanDayCreate(date=date.today()))
    plan = await meal_repo.add(test_user.id, plan)

    assert await meal_repo.get(plan.id, owner_id=intruder.id) is None
    assert await meal_repo.get(plan.id, owner_id=test_user.id) is not None


# ---------------------------------------------------------
# _count
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test__count_returns_correct_number(meal_repo, test_recipe, test_user):
    rec = await test_recipe()
    for i in range(2):
        await meal_repo.add(
            test_user.id,
            MealPlanCreate(
                name=f"P{i}",
                start_date=date.today(),
                end_date=date.today(),
                days=[
                    MealPlanDayCreate(
                        date=date.today(), items=[MealPlanItemCreate(recipe_id=rec.id, meal_type=MealType.breakfast)]
                    )
                ],
            ),
        )

    stmt = select(MealPlan)

    count = await meal_repo._count(stmt)
    assert count == 2


# ---------------------------------------------------------
# _must_get_owned
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test__must_get_owned_success(meal_repo, test_recipe, test_user):
    rec = await test_recipe()
    plan = await meal_repo.add(
        test_user.id,
        _plan_create(rec),
    )
    loaded = await meal_repo._must_get_owned(plan.id, test_user.id)
    assert loaded.id == plan.id


@pytest.mark.asyncio
async def test__must_get_owned_missing(meal_repo, test_user):
    with pytest.raises(HTTPException) as exc:
        await meal_repo._must_get_owned("missing-id", test_user.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test__must_get_owned_forbidden(meal_repo, test_recipe, user_factory, test_user):
    intruder = await user_factory()
    rec = await test_recipe()
    plan = await meal_repo.add(
        test_user.id,
        _plan_create(rec),
    )
    with pytest.raises(HTTPException) as exc:
        await meal_repo._must_get_owned(plan.id, intruder.id)
    assert exc.value.status_code == 403


# ---------------------------------------------------------
# list()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_list_filters_and_paginates(meal_repo, test_recipe, test_user):
    rec = await test_recipe()

    # today
    await meal_repo.add(test_user.id, _plan_create(rec))

    # future
    start_fut = date.today() + timedelta(days=5)
    await meal_repo.add(
        test_user.id,
        MealPlanCreate(
            name="Future",
            start_date=start_fut,
            end_date=start_fut,
            days=[MealPlanDayCreate(date=start_fut)],
        ),
    )

    res = await meal_repo.list(
        owner_id=test_user.id,
        skip=0,
        limit=10,
        start_date=date.today(),
        end_date=None,
    )

    assert res["total"] == 2
    assert len(res["items"]) == 2
    assert res["items"][0].start_date >= res["items"][1].start_date


# ---------------------------------------------------------
# get_visible()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_get_visible_success(meal_repo, test_recipe, test_user):
    rec = await test_recipe()
    plan = await meal_repo.add(test_user.id, _plan_create(rec))

    vis = await meal_repo.get_visible(plan.id, test_user.id)
    assert vis.id == plan.id


@pytest.mark.asyncio
async def test_get_visible_missing(meal_repo, test_user):
    with pytest.raises(HTTPException):
        await meal_repo.get_visible("nope", test_user.id)


@pytest.mark.asyncio
async def test_get_visible_forbidden(meal_repo, test_recipe, user_factory, test_user):
    intruder = await user_factory()
    rec = await test_recipe()
    plan = await meal_repo.add(test_user.id, _plan_create(rec))

    with pytest.raises(HTTPException):
        await meal_repo.get_visible(plan.id, intruder.id)


# ---------------------------------------------------------
# get_current()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_get_current_success(meal_repo, test_recipe, test_user):
    rec = await test_recipe()
    await meal_repo.add(test_user.id, _plan_create(rec))
    plan = await meal_repo.get_current(owner_id=test_user.id)
    assert plan is not None


@pytest.mark.asyncio
async def test_get_current_not_found(meal_repo, test_user):
    with pytest.raises(HTTPException):
        await meal_repo.get_current(owner_id=test_user.id)


# ---------------------------------------------------------
# update() full days replacement
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_update_replaces_days(meal_repo, test_recipe, test_user):
    rec1 = await test_recipe("A")
    rec2 = await test_recipe("B")

    plan = await meal_repo.add(
        test_user.id,
        MealPlanCreate(
            name="Orig",
            start_date=date.today(),
            end_date=date.today(),
            days=[
                MealPlanDayCreate(
                    date=date.today(),
                    items=[MealPlanItemCreate(recipe_id=rec1.id, meal_type=MealType.lunch)],
                )
            ],
        ),
    )

    # Replace days entirely
    patch = MealPlanUpdate(
        name="New",
        days=[
            MealPlanDayUpdate(
                date=date.today(),
                notes=None,
                items=[
                    MealPlanItemUpdate(
                        recipe_id=rec2.id,
                        meal_type=MealType.dinner,
                        servings=1,
                        notes=None,
                    )
                ],
            )
        ],
    )

    updated = await meal_repo.update(plan.id, test_user.id, patch)

    assert updated.name == "New"
    assert updated.days[0].items[0].recipe_id == rec2.id


# ---------------------------------------------------------
# delete()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_removes_plan(meal_repo, test_recipe, test_user):
    rec = await test_recipe()
    plan = await meal_repo.add(test_user.id, _plan_create(rec))

    await meal_repo.delete(plan.id, owner_id=test_user.id)
    assert await meal_repo.get(plan.id, test_user.id) is None


# ---------------------------------------------------------
# generate()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_creates_days_and_items(meal_repo, test_recipe, test_user):
    await test_recipe("R1")
    await test_recipe("R2")

    plan = await meal_repo.generate(
        owner_id=test_user.id,
        start_date=date.today(),
        days=3,
        meals_per_day=[MealType.breakfast, MealType.dinner],
        max_prep_time=None,
        preferred_categories=None,
        excluded_categories=None,
    )

    assert len(plan.days) == 3
    for d in plan.days:
        assert len(d.items) == 2


@pytest.mark.asyncio
async def test_generate_no_recipes_error(meal_repo, test_user):
    with pytest.raises(HTTPException):
        await meal_repo.generate(
            owner_id=test_user.id,
            start_date=date.today(),
            days=1,
            meals_per_day=[MealType.breakfast],
            max_prep_time=None,
            preferred_categories=None,
            excluded_categories=None,
        )


# ---------------------------------------------------------
# shopping_list()
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_shopping_list_combines_ingredients(meal_repo, db_session, test_user, test_recipe):
    rec1 = await test_recipe("R1")
    rec2 = await test_recipe("R2")

    rec1.ingredients = [RecipeIngredient(name="Egg", quantity="2", unit="pcs", order=0)]
    rec2.ingredients = [RecipeIngredient(name="Egg", quantity="3", unit="pcs", order=0)]
    db_session.add_all([rec1, rec2])
    await db_session.commit()

    plan = await meal_repo.add(
        test_user.id,
        MealPlanCreate(
            name="Plan",
            start_date=date.today(),
            end_date=date.today(),
            days=[
                MealPlanDayCreate(
                    date=date.today(),
                    items=[
                        MealPlanItemCreate(recipe_id=rec1.id, meal_type=MealType.lunch),
                        MealPlanItemCreate(recipe_id=rec2.id, meal_type=MealType.dinner),
                    ],
                )
            ],
        ),
    )

    sl = await meal_repo.shopping_list(plan.id, owner_id=test_user.id)

    egg = sl["items"][0]
    assert egg["name"] == "Egg"
    assert egg["quantity"] == "5.0"
    assert set(egg["recipes"]) == {"R1", "R2"}


# ---------------------------------------------------------
# _validate_recipes
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_validate_recipes_missing(meal_repo, test_user):
    bad = MealPlanCreate(
        name="Bad",
        start_date=date.today(),
        end_date=date.today(),
        days=[
            MealPlanDayCreate(
                date=date.today(),
                items=[MealPlanItemCreate(recipe_id="missing", meal_type=MealType.lunch)],
            )
        ],
    )
    with pytest.raises(HTTPException):
        await meal_repo._validate_recipes(bad, test_user.id)


@pytest.mark.asyncio
async def test_validate_recipes_no_items_ok(meal_repo, test_user):
    good = MealPlanCreate(
        name="Good",
        start_date=date.today(),
        end_date=date.today(),
        days=[MealPlanDayCreate(date=date.today(), items=[])],
    )
    await meal_repo._validate_recipes(good, test_user.id)
