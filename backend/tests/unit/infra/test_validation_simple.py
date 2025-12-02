import pytest
from cfgv import ValidationError

from app.infra.validation_simple import ValidationSimple, coerce_int, coerce_minutes, parse_time_str
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate, RecipeInstructionCreate, RecipeNutritionBase


@pytest.mark.parametrize(
    "s,expected",
    [
        ("1h 30m", 90),
        ("45 min", 45),
        ("2h", 120),
        ("  3h   5m ", 185),
        ("0h 0m", None),  # regex returns None when both 0
        ("n/a", None),
        (None, None),
        (123, None),
    ],
)
def test_parse_time_variants(s, expected):
    assert parse_time_str(s) == expected


# ---------- ValidationSimple.validate tests ----------


@pytest.mark.asyncio
async def test_happy_path_minimal():
    svc = ValidationSimple()
    classification = {
        "title": " Roasted Squash ",
        "description": "Test desc",
        "ingredients": [{"name": "butternut squash", "quantity": "1", "unit": "kg", "preparation": "peeled"}],
        "instructions": [{"instruction": " Preheat oven to 200°C. "}, {"instruction": " Roast for 30 minutes. "}],
        "prep_time": "15 m",
        "cook_time": "45 m",
        "servings": "4",
        # other keys intentionally omitted
    }
    dto: RecipeCreate = await svc.validate(classification, thumbnail_filename="thumb.jpg")

    assert isinstance(dto, RecipeCreate)
    assert dto.title == "Roasted Squash"  # trimmed
    assert dto.description == "Test desc"
    assert dto.prep_time == 15
    assert dto.cook_time == 45
    assert dto.servings == 4
    assert dto.image_url == "thumb.jpg"  # falls back to thumbnail since none provided
    assert len(dto.ingredients) == 1
    ing = dto.ingredients[0]
    assert (ing.name, ing.quantity, ing.unit, ing.preparation) == ("butternut squash", "1", "kg", "peeled")
    assert len(dto.instructions) == 2
    assert dto.instructions[0].step == 1
    assert dto.instructions[0].instruction == "Preheat oven to 200°C."
    assert dto.instructions[1].step == 2
    assert dto.instructions[1].instruction == "Roast for 30 minutes."


@pytest.mark.asyncio
async def test_description_non_string_becomes_none():
    svc = ValidationSimple()
    dto = await svc.validate(
        {
            "title": "A",
            "description": {"not": "a string"},
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do y"}],
        },
        thumbnail_filename="t.jpg",
    )
    assert dto.description is None


@pytest.mark.asyncio
async def test_servings_coercion_and_invalid():
    svc = ValidationSimple()
    # valid numeric string
    dto1 = await svc.validate(
        {"title": "A", "servings": "6", "ingredients": [{"name": "x"}], "instructions": [{"instruction": "Do y"}]},
        thumbnail_filename="t.jpg",
    )
    assert dto1.servings == 6

    # invalid -> None
    dto2 = await svc.validate(
        {"title": "A", "servings": "six", "ingredients": [{"name": "x"}], "instructions": [{"instruction": "Do y"}]},
        thumbnail_filename="t.jpg",
    )
    assert dto2.servings is None

    # missing -> None
    dto3 = await svc.validate(
        {"title": "A", "ingredients": [{"name": "x"}], "instructions": [{"instruction": "Do y"}]},
        thumbnail_filename="t.jpg",
    )
    assert dto3.servings is None


@pytest.mark.asyncio
async def test_ingredients_required_and_nonempty():
    svc = ValidationSimple()

    with pytest.raises(ValidationError, match="No valid ingredients"):
        await svc.validate({"title": "A", "ingredients": [], "instructions": [{"instruction": "Do"}]}, "t.jpg")

    with pytest.raises(ValidationError, match="No valid ingredients"):
        await svc.validate({"title": "A", "instructions": [{"instruction": "Do"}]}, "t.jpg")


@pytest.mark.asyncio
async def test_instructions_required_and_nonempty():
    svc = ValidationSimple()

    with pytest.raises(ValidationError, match="No valid instructions"):
        await svc.validate({"title": "A", "ingredients": [{"name": "x"}], "instructions": []}, "t.jpg")

    with pytest.raises(ValidationError, match="No valid instructions"):
        await svc.validate({"title": "A", "ingredients": [{"name": "x"}]}, "t.jpg")


@pytest.mark.asyncio
async def test_instruction_numbering_is_sequential_now():
    """
    New policy: steps are re-numbered deterministically 1..N.
    Any provided 'step' values from input are ignored.
    """
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [{"name": "x"}],
        "instructions": [
            {"instruction": "first"},
            {"step": 7, "instruction": "second"},
            "third",
        ],
    }
    dto = await svc.validate(data, "t.jpg")
    assert [s.step for s in dto.instructions] == [1, 2, 3]
    assert [s.instruction for s in dto.instructions] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_instruction_trimmed_and_empty_skipped():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [{"name": "x"}],
        "instructions": [
            {"instruction": "  trimmed  "},
            {"instruction": "   "},  # empty after trim -> dropped
            {"text": ""},  # empty -> dropped
        ],
    }
    dto = await svc.validate(data, "t.jpg")
    assert len(dto.instructions) == 1
    assert dto.instructions[0].instruction == "trimmed"


@pytest.mark.asyncio
async def test_image_prefers_provided_else_thumbnail():
    svc = ValidationSimple()
    # provided `image_url` wins
    dto = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "image_url": "https://img/abc.jpg",
        },
        thumbnail_filename="thumb.jpg",
    )
    assert dto.image_url == "https://img/abc.jpg"

    # missing -> fallback to thumbnail
    dto2 = await svc.validate(
        {"title": "A", "ingredients": [{"name": "x"}], "instructions": [{"instruction": "Do"}]},
        thumbnail_filename="thumb.jpg",
    )
    assert dto2.image_url == "thumb.jpg"


@pytest.mark.asyncio
async def test_all_instructions_empty_leads_to_validation_error():
    svc = ValidationSimple()
    with pytest.raises(ValidationError, match="No valid instructions"):
        await svc.validate(
            {"title": "A", "ingredients": [{"name": "x"}], "instructions": [{"step": 1}]},  # no text
            "t.jpg",
        )


@pytest.mark.asyncio
async def test_accepts_typed_objects_from_frontend():
    svc = ValidationSimple()
    data = {
        "title": "Typed",
        "ingredients": [RecipeIngredientCreate(name="Flour", quantity="200", unit="g")],
        "instructions": [RecipeInstructionCreate(step=5, instruction="Mix")],  # will be renumbered to 1
        "prep_time": 10,  # already ints are accepted
        "cook_time": 0,
        "servings": 2,
        "image_url": "img.png",
    }
    dto = await svc.validate(data, "thumb.jpg")
    assert dto.title == "Typed"
    assert dto.prep_time == 10
    assert dto.cook_time == 0
    assert dto.servings == 2
    assert dto.instructions[0].step == 1
    assert dto.image_url == "img.png"


# ---------------------------------------------------------------------------
# coerce_minutes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "val,expected",
    [
        (None, None),
        (5, 5),  # int passthrough
        ("1h", 60),  # valid str
        ("bad", None),  # invalid str
        ([], None),  # type -> None
    ],
)
def test_coerce_minutes_cases(val, expected):
    assert coerce_minutes(val) == expected


# ---------------------------------------------------------------------------
# coerce_int
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "val,expected",
    [
        ("10", 10),
        (" 7 ", 7),
        ("", None),
        ("   ", None),
        (None, None),
        ("abc", None),
        (12.5, 12),  # coercible
        (True, 1),
    ],
)
def test_coerce_int_cases(val, expected):
    assert coerce_int(val) == expected


# ---------------------------------------------------------------------------
# Ingredient normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingredient_text_fallback_and_qty_fallback():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [
            {"text": "Carrot"},
            {"name": "Flour", "qty": "250"},
        ],
        "instructions": [{"instruction": "Do"}],
    }
    dto = await svc.validate(data, "t.jpg")

    assert len(dto.ingredients) == 2
    assert dto.ingredients[0].name == "Carrot"
    assert dto.ingredients[1].quantity == "250"  # qty fallback


@pytest.mark.asyncio
async def test_ingredient_strings_are_converted_to_name_only():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": ["salt", 123],
        "instructions": [{"instruction": "Do"}],
    }
    dto = await svc.validate(data, "t.jpg")

    names = [i.name for i in dto.ingredients]
    assert names == ["salt", "123"]
    for ing in dto.ingredients:
        assert ing.quantity is None
        assert ing.unit is None
        assert ing.preparation is None


@pytest.mark.asyncio
async def test_ingredient_empty_names_are_dropped_and_if_all_dropped_raise():
    svc = ValidationSimple()

    # Case 1 — empty names dropped, but others valid
    dto = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "  "}, {"text": ""}, {"text": "Ok"}],
            "instructions": [{"instruction": "Do"}],
        },
        "t.jpg",
    )
    assert len(dto.ingredients) == 1
    assert dto.ingredients[0].name == "Ok"

    # Case 2 — all dropped => validation error
    with pytest.raises(ValidationError, match="No valid ingredients"):
        await svc.validate(
            {
                "title": "A",
                "ingredients": [{"name": "   "}, {"text": ""}],
                "instructions": [{"instruction": "Do"}],
            },
            "t.jpg",
        )


# ---------------------------------------------------------------------------
# Instruction normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instruction_text_key_and_nonstring_coercion():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [{"name": "x"}],
        "instructions": [
            {"text": "Chop carrots"},
            123,
            True,
        ],
    }
    dto = await svc.validate(data, "t.jpg")

    assert [s.instruction for s in dto.instructions] == [
        "Chop carrots",
        "123",
        "True",
    ]


@pytest.mark.asyncio
async def test_all_instruction_text_empty_triggers_error():
    svc = ValidationSimple()

    with pytest.raises(ValidationError, match="No valid instructions"):
        await svc.validate(
            {
                "title": "A",
                "ingredients": [{"name": "x"}],
                "instructions": [
                    {"instruction": ""},  # empty
                    {"text": "   "},  # empty after strip
                ],
            },
            "t.jpg",
        )


# ---------------------------------------------------------------------------
# Nutrition assembly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nutrition_valid_dict_creates_model():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [{"name": "x"}],
        "instructions": [{"instruction": "Do"}],
        "nutrition": {"calories": 100},
    }
    dto = await svc.validate(data, "t.jpg")

    assert isinstance(dto.nutrition, RecipeNutritionBase)
    assert dto.nutrition.calories == 100


@pytest.mark.asyncio
async def test_nutrition_invalid_dict_becomes_none():
    svc = ValidationSimple()
    data = {
        "title": "A",
        "ingredients": [{"name": "x"}],
        "instructions": [{"instruction": "Do"}],
        "nutrition": {"calories": "not an int"},
    }
    dto = await svc.validate(data, "t.jpg")

    assert dto.nutrition is None


# ---------------------------------------------------------------------------
# Categories / tags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_categories_and_tags_must_be_lists_or_become_empty():
    svc = ValidationSimple()
    dto = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "categories": "not a list",
            "tags": None,
        },
        "t.jpg",
    )

    assert dto.categories == []
    assert dto.tags == []

    dto2 = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "categories": ["A", "B"],
            "tags": ["C"],
        },
        "t.jpg",
    )

    assert dto2.categories == ["A", "B"]
    assert dto2.tags == ["C"]


# ---------------------------------------------------------------------------
# Image fallback edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_blank_fallback_and_thumbnail_blank_yields_none():
    svc = ValidationSimple()

    # blank image_url → fallback to thumbnail
    dto = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "image_url": "   ",
        },
        thumbnail_filename="thumb.jpg",
    )
    assert dto.image_url == "thumb.jpg"

    # both blank -> None
    dto2 = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "image_url": "",
        },
        thumbnail_filename="",
    )
    assert dto2.image_url is None


# ---------------------------------------------------------------------------
# Title trimming and non-string handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_title_trim_and_nonstring_raises_validation_error():
    svc = ValidationSimple()

    # valid title → trimmed
    dto = await svc.validate(
        {
            "title": "  Pancakes  ",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
        },
        "t.jpg",
    )
    assert dto.title == "Pancakes"

    # non-string title → should raise ValidationError
    with pytest.raises(ValidationError, match="title is missing"):
        await svc.validate(
            {
                "title": 123,
                "ingredients": [{"name": "x"}],
                "instructions": [{"instruction": "Do"}],
            },
            "t.jpg",
        )


# ---------------------------------------------------------------------------
# Source passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_and_source_url_passthrough():
    svc = ValidationSimple()
    dto = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
            "source": "Grandma",
            "source_url": "https://example.com",
        },
        "t.jpg",
    )

    assert dto.source == "Grandma"
    assert dto.source_url == "https://example.com"

    # missing → None
    dto2 = await svc.validate(
        {
            "title": "A",
            "ingredients": [{"name": "x"}],
            "instructions": [{"instruction": "Do"}],
        },
        "t.jpg",
    )
    assert dto2.source is None
    assert dto2.source_url is None
