import re
from typing import Any, Dict, List, Optional

from cfgv import ValidationError

from app.ports.validation import ValidationService
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate, RecipeInstructionCreate, RecipeNutritionBase

_TIME_RE = re.compile(
    r"^\s*(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*$",
    re.IGNORECASE,
)


def parse_time_str(s: Optional[str]) -> Optional[int]:
    if not isinstance(s, str):
        return None
    m = _TIME_RE.fullmatch(s.strip())
    if not m:
        return None
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    return h * 60 + mi if (h or mi) else None


def coerce_minutes(val: Any) -> Optional[int]:
    """Accepts int minutes or strings like '1h 30m'/'45 min'."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        return parse_time_str(val)
    return None


def coerce_int(val: Any) -> Optional[int]:
    try:
        return int(val) if val is not None and str(val).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _normalize(input_data: Dict[str, Any], thumbnail: str) -> Dict[str, Any]:
    data: dict[str, Any] = input_data or {}

    title = data.get("title")
    if isinstance(title, str):
        title = title.strip()
    else:
        title = ""
    out = {"title": title}

    # Title / description
    desc = data.get("description")
    out["description"] = desc if isinstance(desc, str) else None

    out["prep_time"] = coerce_minutes(data.get("prep_time"))
    out["cook_time"] = coerce_minutes(data.get("cook_time"))

    # Times: accept int (frontend) or str (LLM)
    if isinstance(data.get("servings"), int):
        out["servings"] = data.get("servings")
    else:
        out["servings"] = coerce_int(data.get("servings"))

    # Image policy: prefer provided image_url; else thumbnail (same rule every run)
    img = data.get("image_url")
    out["image_url"] = (img if isinstance(img, str) and img.strip() else None) or (thumbnail or None)

    # Notes (optional)
    notes = data.get("notes")
    out["notes"] = notes if isinstance(notes, str) else None

    # Ingredients: tolerate dicts or typed objects
    ing_list = data.get("ingredients") or []
    norm_ingredients: List[Dict[str, Any]] = []
    if isinstance(ing_list, list):
        for item in ing_list:
            if isinstance(item, RecipeIngredientCreate):
                norm_ingredients.append(
                    {
                        "name": item.name.strip(),
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "preparation": item.preparation,
                    }
                )
            elif isinstance(item, dict):
                name = (item.get("name") or item.get("text") or "").strip()
                if not name:
                    continue
                norm_ingredients.append(
                    {
                        "name": name,
                        "quantity": item.get("quantity", item.get("qty")),
                        "unit": item.get("unit"),
                        "preparation": item.get("preparation"),
                    }
                )
            else:
                # strings or unknown types ignored in this unified path
                s = str(item).strip()
                if s:
                    norm_ingredients.append({"name": s, "quantity": None, "unit": None, "preparation": None})
    out["ingredients"] = norm_ingredients

    # Instructions: accept strings or typed objects; re-number later
    steps_in = data.get("instructions") or []
    norm_steps: List[str] = []
    if isinstance(steps_in, list):
        for step in steps_in:
            if isinstance(step, RecipeInstructionCreate):
                txt = (step.instruction or "").strip()
            elif isinstance(step, dict):
                txt = (step.get("instruction") or step.get("text") or "").strip()
            else:
                txt = str(step).strip()
            if txt:
                norm_steps.append(txt)

    out["instructions"] = norm_steps

    # Categories / tags (lists of str)
    cats = data.get("categories")
    tags = data.get("tags")
    out["categories"] = cats if isinstance(cats, list) else []
    out["tags"] = tags if isinstance(tags, list) else []

    # Nutrition (dict tolerated)
    out["nutrition"] = data.get("nutrition") if isinstance(data.get("nutrition"), dict) else None

    # Source metadata passthrough if present
    out["source"] = data.get("source")
    out["source_url"] = data.get("source_url")

    return out


def _check_required(d: Dict[str, Any]) -> None:
    if not d["title"]:
        raise ValidationError("Recipe title is missing.")
    if not isinstance(d.get("ingredients"), list) or not d["ingredients"]:
        raise ValidationError("No valid ingredients found.")
    if not isinstance(d.get("instructions"), list) or not d["instructions"]:
        raise ValidationError("No valid instructions/steps found.")


def _assemble(d: Dict[str, Any]) -> RecipeCreate:
    ingredients = [
        RecipeIngredientCreate(
            name=i["name"],
            quantity=i.get("quantity"),
            unit=i.get("unit"),
            preparation=i.get("preparation"),
        )
        for i in d["ingredients"]
    ]
    instructions = [
        RecipeInstructionCreate(step=idx + 1, instruction=text) for idx, text in enumerate(d["instructions"])
    ]
    nutrition = None
    if isinstance(d["nutrition"], dict):
        try:
            nutrition = RecipeNutritionBase(**d["nutrition"])
        except Exception:
            nutrition = None

    return RecipeCreate(
        title=d["title"],
        description=d["description"],
        prep_time=d["prep_time"],
        cook_time=d["cook_time"],
        servings=d["servings"],
        image_url=d["image_url"],
        source=d.get("source"),
        source_url=d.get("source_url"),
        categories=d["categories"],
        tags=d["tags"],
        difficulty=None,
        notes=d["notes"],
        rating=None,
        nutritional_info=None,
        ingredients=ingredients,
        instructions=instructions,
        nutrition=nutrition,
    )


class ValidationSimple(ValidationService):
    """
    Accepts either:
      - LLM output dict (RecipeLLMOut-like), or
      - RecipeCreate (frontend) or its dict
    Returns RecipeCreate or raises ValidationError.
    """

    async def validate(self, input_data: Dict[str, Any], thumbnail_filename: str) -> RecipeCreate:
        # 1. normalize across sources to a single canonical dict
        norm = _normalize(input_data, thumbnail_filename)

        # 2. structural checks (same for all sources)
        _check_required(norm)

        # 3. assemble DTO (deterministic)
        return _assemble(norm)
