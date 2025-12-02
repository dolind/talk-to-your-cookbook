from typing import List, Optional

from app.schemas.ocr import ClassificationGraphPatch, ClassificationGraphState
from app.schemas.recipe import RecipeCreate

ALLOWED_CATEGORIES = {
    "Breakfast",
    "Lunch",
    "Dinner",
    "Dessert",
    "Snack",
    "Soup",
    "Salad",
    "Side",
    "Bread",
    "Drink",
    "Sauce",
    "Vegetarian",
    "Vegan",
    "Gluten-Free",
    "Pasta",
    "Seafood",
    "Meat",
    "Poultry",
    "BBQ",
    "Baking",
    "One-Pot",
    "Quick",
}


def _sanitize_categories(cats: Optional[List[str]]) -> List[str]:
    if not isinstance(cats, list):
        return []
    out: List[str] = []
    for c in cats:
        if not isinstance(c, str):
            continue
        s = c.strip()
        if s and s in ALLOWED_CATEGORIES:
            out.append(s)
    # dedupe in order, cap to 3
    return list(dict.fromkeys(out))[:3]


def _sanitize_tags(tags: Optional[List[str]]) -> List[str]:
    if not isinstance(tags, list):
        return []
    out: List[str] = []
    seen = set()
    for t in tags:
        if not isinstance(t, str):
            continue
        s = t.strip().lower()
        if not s or len(s) > 40:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:12]


async def validate_or_merge_taxonomy(state: ClassificationGraphState) -> ClassificationGraphPatch:
    """
    Sanitize & merge taxonomy into the already-approved recipe.
    Loop back to taxonomy editor on errors.
    """
    recipe: RecipeCreate = state.current_recipe_state
    user_tx = state.taxonomy_user_approved or {}

    # cats = _sanitize_categories(user_tx.get("categories"))
    # tags = _sanitize_tags(user_tx.gt("tags"))
    cats = user_tx.get("categories")
    tags = user_tx.get("tags")

    # if user sent nothing, fall back to suggestion

    recipe.categories = cats
    recipe.tags = tags
    return {
        "current_recipe_state": recipe,
    }
