from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.schemas.ocr import SegmentationGraphState
from app.workflows.segmentation.nodes.approve_segmentation import approve_segmentation
from app.workflows.segmentation.nodes.interrupt_segmentation import interrupt_segmentation
from app.workflows.segmentation.nodes.start_segmentation import start_segmentation


def build_segmentation_graph(checkpointer: InMemorySaver = InMemorySaver()):
    builder = StateGraph(SegmentationGraphState)

    builder.add_node("start_segmentation", start_segmentation)
    builder.add_node("interrupt_segmentation", interrupt_segmentation)
    builder.add_node("approve_segmentation", approve_segmentation)

    builder.add_edge(
        START,
        "start_segmentation",
    )
    builder.add_edge("start_segmentation", "interrupt_segmentation")
    builder.add_edge("interrupt_segmentation", "approve_segmentation")
    builder.add_edge("approve_segmentation", END)

    return builder.compile(checkpointer=checkpointer)
