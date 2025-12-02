from app.schemas.ocr import ClassificationGraphState
from app.workflows.classification.nodes.routers import route_after_validate


def test_route_after_validate_first_pass():
    state = ClassificationGraphState(first_pass_validation=True)
    assert route_after_validate(state) == "to_user_confirmation"


def test_route_after_validate_to_taxonomy():
    state = ClassificationGraphState(first_pass_validation=False)
    assert route_after_validate(state) == "to_taxonomy"
