from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.schemas.ocr import ClassificationGraphState
from app.workflows.classification.nodes.add_categories_tags import enrich_categories_tags
from app.workflows.classification.nodes.approve_classification import approve_classification
from app.workflows.classification.nodes.check_grouping import check_grouping
from app.workflows.classification.nodes.interrupt_classification import interrupt_classification
from app.workflows.classification.nodes.interrupt_taxonomy import interrupt_taxonomy
from app.workflows.classification.nodes.routers import route_after_validate
from app.workflows.classification.nodes.start_classification import start_classification
from app.workflows.classification.nodes.thumbnail import thumbnail_node
from app.workflows.classification.nodes.validate import validation_node
from app.workflows.classification.nodes.validate_or_merge_taxonomy import validate_or_merge_taxonomy


def build_classification_graph(checkpointer: InMemorySaver = InMemorySaver()):
    builder = StateGraph(ClassificationGraphState)

    builder.add_node("check_grouping", check_grouping)
    builder.add_node("start_classification", start_classification)
    builder.add_node("thumbnail", thumbnail_node)
    builder.add_node("validate", validation_node)
    builder.add_node("interrupt_classification", interrupt_classification)
    builder.add_node("enrich_categories_tags", enrich_categories_tags)
    builder.add_node("interrupt_taxonomy", interrupt_taxonomy)
    builder.add_node("validate_or_merge_taxonomy", validate_or_merge_taxonomy)
    builder.add_node("approve_classification", approve_classification)

    builder.add_edge(START, "check_grouping")

    builder.add_edge("check_grouping", "thumbnail")
    builder.add_edge("check_grouping", "start_classification")

    builder.add_edge("start_classification", "validate")
    builder.add_edge("thumbnail", "validate")

    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "to_user_confirmation": "interrupt_classification",
            "to_taxonomy": "enrich_categories_tags",
        },
    )

    # after the first interrupt rerun validate
    builder.add_edge("interrupt_classification", "validate")

    # 2nd pass will add taxonomy
    builder.add_edge("enrich_categories_tags", "interrupt_taxonomy")
    builder.add_edge("interrupt_taxonomy", "validate_or_merge_taxonomy")

    builder.add_edge("validate_or_merge_taxonomy", "approve_classification")

    builder.add_edge("approve_classification", END)

    return builder.compile(checkpointer=checkpointer)
