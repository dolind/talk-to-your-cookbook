from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.meal_plan import MealPlan
from app.models.recipe import Recipe


@pytest.mark.asyncio
async def test_create_meal_plan(authed_client_session: AsyncClient, db_session, test_user):
    recipe = Recipe(user_id=test_user.id, title="Oats", prep_time=5, cook_time=5, servings=1)
    db_session.add(recipe)
    await db_session.commit()

    payload = {
        "name": "Test Plan",
        "description": "A sample plan",
        "start_date": str(date.today()),
        "end_date": str(date.today()),
        "days": [
            {
                "date": str(date.today()),
                "notes": "Healthy start",
                "items": [{"recipe_id": recipe.id, "meal_type": "breakfast", "servings": 1, "notes": ""}],
            }
        ],
    }

    response = await authed_client_session.post("/api/v1/meal-plans/", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Plan"


@pytest.mark.asyncio
async def test_get_meal_plans(authed_client_session: AsyncClient):
    response = await authed_client_session.get("/api/v1/meal-plans/")
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_generate_meal_plan(authed_client_session: AsyncClient, db_session, test_user):
    recipe = Recipe(user_id=test_user.id, title="Smoothie", prep_time=5, cook_time=0, servings=1)
    db_session.add(recipe)
    await db_session.commit()

    payload = {"start_date": str(date.today()), "days": 7, "meals_per_day": ["breakfast"], "max_prep_time": 10}

    response = await authed_client_session.post("/api/v1/meal-plans/generate", json=payload)
    assert response.status_code == 200
    assert response.json()["name"].startswith("Meal Plan")


@pytest.mark.asyncio
async def test_get_current_meal_plan_not_found(authed_client_session: AsyncClient):
    response = await authed_client_session.get("/api/v1/meal-plans/current")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_meal_plan(authed_client_session: AsyncClient, db_session, test_user):
    meal_plan = MealPlan(user_id=test_user.id, name="To Delete", start_date=date.today(), end_date=date.today())
    db_session.add(meal_plan)
    await db_session.commit()

    response = await authed_client_session.delete(f"/api/v1/meal-plans/{meal_plan.id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_update_meal_plan(authed_client_session: AsyncClient, db_session, test_user):
    recipe = Recipe(user_id=test_user.id, title="Updated Dish", prep_time=10, cook_time=15, servings=2)
    meal_plan = MealPlan(
        user_id=test_user.id,
        name="Original Plan",
        description="Original description",
        start_date=date.today(),
        end_date=date.today(),
    )
    db_session.add_all([recipe, meal_plan])
    await db_session.commit()
    await db_session.refresh(meal_plan)

    update_payload = {
        "name": "Updated Plan",
        "description": "New description",
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=1)),
        "days": [
            {
                "date": str(date.today()),
                "notes": "Updated notes",
                "items": [{"recipe_id": recipe.id, "meal_type": "lunch", "servings": 1, "notes": "Try with salad"}],
            }
        ],
    }

    response = await authed_client_session.put(f"/api/v1/meal-plans/{meal_plan.id}", json=update_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Plan"
    assert body["description"] == "New description"
    assert len(body["days"]) == 1
