from fastapi import APIRouter

from app.routes import auth, chat, embeddings, meal_plans, recipes, recipescanner, shopping_list, status, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(meal_plans.router, prefix="/meal-plans", tags=["meal-plans"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(shopping_list.router, prefix="/shoppinglist", tags=["shoppinglist"])
api_router.include_router(recipescanner.router, prefix="/recipescanner", tags=["recipescanner"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])

api_router.include_router(status.router, prefix="", tags=["ws"])
