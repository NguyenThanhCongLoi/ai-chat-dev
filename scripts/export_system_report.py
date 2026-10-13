"""Export the reviewed system report and inventories without reading live data."""
import ast
import csv
from pathlib import Path
import generate_companion_function_report as exporter
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/AI_COMPANION_SYSTEM_REPORT.md"


def export_inventories():
    routes, modules = [], []
    for path in sorted((ROOT / "character_chat").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        relative = path.relative_to(ROOT).as_posix()
        modules.append([relative, 1, "module", ""])
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            modules.append([relative, node.lineno, type(node).__name__, node.name])
            for decorator in getattr(node, "decorator_list", []):
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr.upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                    continue
                if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                    routes.append([relative, node.lineno, method, decorator.args[0].value, node.name])
    for name, header, rows in [
        ("API", ["Source", "Line", "Method", "Path", "Handler"], routes),
        ("MODULE", ["Source", "Line", "Kind", "Symbol"], modules),
    ]:
        target = ROOT / "docs" / f"AI_COMPANION_{name}_INVENTORY.csv"
        with target.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        print(target, len(rows))


if __name__ == "__main__":
    exporter.SOURCE = SOURCE
    exporter.WORD = ROOT / "reports/AI_Companion_System_Report_2026-10-13.docx"
    exporter.WORD.parent.mkdir(exist_ok=True)
    result = exporter.export_word()
    document = Document(result)
    document.core_properties.title = "Báo cáo toàn hệ thống AI Companion — 13/10/2026"
    document.core_properties.subject = "Tính năng, thuật toán, module, dữ liệu và giới hạn"
    document.save(result)
    print(result)
    export_inventories()
