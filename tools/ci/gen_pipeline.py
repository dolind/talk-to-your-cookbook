"""Generate a LangGraph pipeline visualization as SVG using Graphviz."""

import importlib
import pkgutil
import sys
from pathlib import Path

import networkx as nx
from pygraphviz import AGraph

from app.models import chat, meal_plan, ocr, recent_recipe, recipe, shopping_list, user
from app.workflows.classification.graph_builder import build_classification_graph
from app.workflows.recipeassistant.chat_graph_definition import build_simple_rag_graph
from app.workflows.segmentation.graph_builder import build_segmentation_graph

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


OUTPUT_PATH = Path("docs/diagrams/graphs/")


def import_all_models():
    pkg = importlib.import_module("app.models")
    for _, module_name, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(module_name)


def main() -> None:
    diagram = build_classification_graph().get_graph().draw_mermaid()

    out = OUTPUT_PATH / "classification.mmd"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(diagram, encoding="utf-8")

    diagram = build_segmentation_graph().get_graph().draw_mermaid()

    out = OUTPUT_PATH / "segmentation.mmd"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(diagram, encoding="utf-8")

    diagram = build_simple_rag_graph(None).get_graph().draw_mermaid()

    out = OUTPUT_PATH / "chat_app.mmd"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(diagram, encoding="utf-8")


if __name__ == "__main__":
    main()
