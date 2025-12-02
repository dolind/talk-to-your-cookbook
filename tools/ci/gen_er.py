"""Generate deterministic Mermaid ER diagram from SQLAlchemy models."""

import sys
from pathlib import Path
from typing import List

from sqlalchemy import ForeignKeyConstraint, Table
from sqlalchemy.orm import DeclarativeMeta

from app import models  # ensure metadata is populated
from app.database.base import Base
from app.models import chat, meal_plan, ocr, recent_recipe, recipe, shopping_list, user

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

OUTPUT = Path("docs/diagrams/er.mmd")


def render_table(table: Table) -> List[str]:
    lines = []
    lines.append(f"    {table.name} {{\n")

    # Columns sorted by name
    cols = sorted(table.columns, key=lambda c: c.name)
    for col in cols:
        coltype = str(col.type)
        name = col.name
        lines.append(f"        {coltype} {name}\n")

    lines.append("    }\n")
    return lines


def render_relationships(table: Table) -> List[str]:
    rels = []
    for fk in table.constraints:
        if isinstance(fk, ForeignKeyConstraint):
            for elem in fk.elements:
                parent = elem.column.table.name
                child = table.name
                # sorted tuple ordering enforced at caller level
                rels.append((parent, child, "foreign_key"))
    return rels


def main() -> None:
    metadata = Base.metadata

    # Sort tables deterministically
    tables = sorted(metadata.tables.values(), key=lambda t: t.name)

    output_lines = ["erDiagram\n"]

    # Collect relationship triples first
    all_rels = []
    for table in tables:
        all_rels.extend(render_relationships(table))

    # Sort relationships globally to guarantee stability
    all_rels = sorted(all_rels, key=lambda t: (t[0], t[1], t[2]))

    # Emit tables
    for table in tables:
        output_lines.extend(render_table(table))
        output_lines.append("\n")

    # Emit relationships
    for parent, child, label in all_rels:
        output_lines.append(f"    {parent} ||--o{{ {child} : {label}\n")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(output_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
