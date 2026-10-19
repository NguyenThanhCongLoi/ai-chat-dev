"""Export current SQLAlchemy schema to DBML, without opening the product DB."""
import argparse
import json
import sys
from pathlib import Path
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.sqlite import dialect
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from character_chat.models import Base

ROOT = Path(__file__).resolve().parents[1]

def quote(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "") + "'"

def columns(names):
    items = list(names)
    return items[0] if len(items) == 1 else "(" + ", ".join(items) + ")"

def export(target):
    lines = [
        "// Generated from character_chat/models.py; contains schema only, no user data.",
        "// Existing databases may differ in nullability/defaults after legacy ALTER TABLE migrations.",
        "// ORM defaults are notes, not SQL DEFAULT constraints. Only declared foreign keys are drawn.",
        "Project AI_Companion {",
        "  database_type: 'SQLite'",
        "  Note: 'Current application schema. Timestamps/JSON/UUID-like IDs retain their actual VARCHAR/TEXT types. Not a PostgreSQL migration.'",
        "}", "",
    ]
    refs = []
    tables = sorted(Base.metadata.tables.values(), key=lambda item: item.name)
    count_columns = count_indexes = 0
    for table in tables:
        pk = [c.name for c in table.primary_key.columns]
        unique_sets = [tuple(c.name for c in constraint.columns) for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
        unique_sets.extend(tuple(c.name for c in idx.columns) for idx in table.indexes if idx.unique)
        lines.append("Table " + table.name + " {")
        for column in table.columns:
            count_columns += 1
            settings = []
            if len(pk) == 1 and column.name == pk[0]:
                settings.append("pk")
            settings.append("null" if column.nullable else "not null")
            notes = []
            if column.default is not None:
                arg = column.default.arg
                value = (getattr(arg, "__name__", "callable") + "()") if callable(arg) else repr(arg)
                notes.append("Application default: " + value + "; supplied by SQLAlchemy, not SQL DEFAULT")
            if column.server_default is not None:
                settings.append("default: " + chr(96) + str(column.server_default.arg) + chr(96))
            if column.name == "spec":
                notes.append("CharacterSpec JSON stored as TEXT")
            if column.name == "content" and str(column.type).upper() == "BLOB":
                notes.append("Binary asset/file/audio content")
            if column.name.endswith("_id") and not column.foreign_keys:
                notes.append("No database FK declared; value may be managed by application logic")
            if notes:
                settings.append("note: " + quote("; ".join(notes)))
            kind = column.type.compile(dialect=dialect()).lower()
            lines.append("  " + column.name + " " + kind + " [" + ", ".join(settings) + "]")
        indexes = []
        if len(pk) > 1:
            indexes.append("    " + columns(pk) + " [pk]")
        for idx in sorted(table.indexes, key=lambda item: item.name or ""):
            flags = ["name: " + quote(idx.name)] if idx.name else []
            if idx.unique:
                flags.append("unique")
            indexes.append("    " + columns(c.name for c in idx.columns) + (" [" + ", ".join(flags) + "]" if flags else ""))
            count_indexes += 1
        for constraint in sorted((c for c in table.constraints if isinstance(c, UniqueConstraint)), key=lambda item: tuple(c.name for c in item.columns)):
            flags = ["unique"]
            if constraint.name:
                flags.append("name: " + quote(constraint.name))
            indexes.append("    " + columns(c.name for c in constraint.columns) + " [" + ", ".join(flags) + "]")
        if indexes:
            lines.extend(["", "  indexes {", *indexes, "  }"])
        lines.extend(["}", ""])
        for fk in sorted(table.foreign_key_constraints, key=lambda item: tuple(c.name for c in item.columns)):
            local = tuple(c.name for c in fk.columns)
            remote = tuple(element.column.name for element in fk.elements)
            destination = next(iter(fk.elements)).column.table.name
            operator = "-" if local == tuple(pk) or local in unique_sets else ">"
            refs.append("Ref: " + table.name + "." + columns(local) + " " + operator + " " + destination + "." + columns(remote))
    lines.extend(["// Only SQLAlchemy-declared FK constraints; no inferred relationships.", *refs, ""])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return {"tables": len(tables), "columns": count_columns, "foreign_keys": len(refs), "indexes": count_indexes}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/database/ai_companion.dbml")
    args = parser.parse_args()
    print(json.dumps(export(args.output), ensure_ascii=False))
    print(args.output)
