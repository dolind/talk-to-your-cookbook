from app.schemas.ocr import ClassificationGraphState


def route_after_validate(state: ClassificationGraphState) -> str:
    # simple routing, no error handling if the user send bad data to validation

    if state.first_pass_validation:
        return "to_user_confirmation"
    return "to_taxonomy"
