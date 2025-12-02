"""Generate a deterministic Mermaid class diagram from Pydantic schemas."""

import importlib
import os
import pkgutil
import sys
import types
from pathlib import Path

import pydantic_mermaid.mermaid_generator as mg
from pydantic import BaseModel
from pydantic_mermaid import MermaidGenerator as Mermaid

# ---------------------------------------------------------------------------
# 1. Ensure deterministic hashing
# ---------------------------------------------------------------------------
# This makes all dict iteration stable.
os.environ.setdefault("PYTHONHASHSEED", "0")


# ---------------------------------------------------------------------------
# 2. Patch MermaidGenerator to make its output deterministic
# ---------------------------------------------------------------------------
# pydantic-mermaid stores graph nodes inside self.nodes (dict)
# and relations inside self.edges (list of tuples).

from copy import deepcopy

from pydantic_mermaid.mermaid_generator import MermaidGenerator, render
from pydantic_mermaid.models import Relations


def deterministic_generate_chart(self, *, root: str = "", relations: Relations = Relations.Dependency) -> str:
    self.generate_allow_list(root, relations)

    # Sort allow_set for stability
    allowed = sorted(self.allow_set)

    final_classes = []
    for class_name in allowed:
        class_value = self.graph.class_dict[class_name]
        final_class = deepcopy(class_value)

        parent_class_name = ""
        if class_name in self.graph.child_parents:
            parent_class_name = sorted(self.graph.child_parents[class_name])[0]

        if parent_class_name in allowed and relations != Relations.Dependency:
            inherited = {str(p) for p in self.graph.class_dict[parent_class_name].properties}
            final_class.properties = [p for p in final_class.properties if str(p) not in inherited]

        final_classes.append(final_class)

    # Sort final classes
    final_classes = sorted(final_classes, key=lambda c: c.name)

    # Deterministic relationships
    def sorted_relationships(rel_dict):
        out = []
        for entity in sorted(rel_dict):
            if entity not in allowed:
                continue
            for related in sorted(rel_dict[entity]):
                out.append((entity, related))
        return out

    client_services = []
    if Relations.Dependency & relations:
        client_services = sorted_relationships(self.graph.service_clients)

    parent_children = []
    if Relations.Inheritance & relations:
        parent_children = sorted_relationships(self.graph.parent_children)

    return render(final_classes, client_services, parent_children)


# Patch class
MermaidGenerator.generate_chart = deterministic_generate_chart


# ---------------------------------------------------------------------------
# 3. Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SCHEMAS_PACKAGE = "app.schemas"
OUTPUT_PATH = Path("docs/diagrams/schemas/")


# ---------------------------------------------------------------------------
# 4. Collect schema modules in deterministic order
# ---------------------------------------------------------------------------
def collect_schema_modules() -> list:
    package = importlib.import_module(SCHEMAS_PACKAGE)

    module_names = [
        module_name for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + ".")
    ]

    module_names.sort()  # deterministic order
    return [importlib.import_module(name) for name in module_names]


# ---------------------------------------------------------------------------
# 5. Collect models within a module in deterministic order
# ---------------------------------------------------------------------------
def collect_models(module) -> list:
    models = []
    for attr in vars(module).values():
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr is not BaseModel:
            models.append(attr)

    models.sort(key=lambda m: m.__name__)
    return models


# ---------------------------------------------------------------------------
# 6. Build synthetic module with ordered model attributes
# ---------------------------------------------------------------------------
def make_ordered_module(real_module) -> types.ModuleType:
    ordered_models = collect_models(real_module)
    tmp = types.ModuleType(real_module.__name__)

    for model in ordered_models:
        setattr(tmp, model.__name__, model)

    return tmp


# ---------------------------------------------------------------------------
# 7. Helper: remove fenced code
# ---------------------------------------------------------------------------
def extract_inner(diagram: str) -> str:
    lines = diagram.strip().splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1])
    return diagram


# ---------------------------------------------------------------------------
# 8. Main
# ---------------------------------------------------------------------------
def main() -> None:
    modules = collect_schema_modules()

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    for module in modules:
        ordered_module = make_ordered_module(module)
        chart = extract_inner(Mermaid(ordered_module).generate_chart())

        name = module.__name__.split(".")[-1]
        (OUTPUT_PATH / f"{name}.mmd").write_text(chart, encoding="utf-8")


if __name__ == "__main__":
    main()
