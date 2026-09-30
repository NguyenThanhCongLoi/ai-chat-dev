"""Refresh the endpoint inventory embedded in the engineering guide."""
from pathlib import Path
from character_chat.main import app

START="<!-- API_INVENTORY_START -->"
END="<!-- API_INVENTORY_END -->"
METHODS=("get","post","put","patch","delete")

def render():
    schema=app.openapi();rows=[]
    for path,operations in schema.get("paths",{}).items():
        for method in METHODS:
            operation=operations.get(method)
            if not operation:continue
            tags=operation.get("tags") or ["System"]
            rows.append((tags[0],path,method.upper(),operation.get("summary") or operation.get("operationId","").replace("_"," ")))
    rows.sort(key=lambda item:(item[0],item[1],item[2]))
    lines=[START,"","## Phụ lục A — toàn bộ HTTP API","",f"Tổng cộng **{len(rows)} operations**. Bảng này được sinh từ FastAPI OpenAPI bằng `scripts/update_architecture_api_inventory.py`.","","| Nhóm | Method | Path | Operation |","|---|---|---|---|"]
    for tag,path,method,summary in rows:
        lines.append(f"| {tag} | `{method}` | `{path}` | {summary.replace('|','/')} |")
    lines.extend(["",END])
    return "\n".join(lines)

def main():
    path=Path(__file__).resolve().parents[1]/"docs"/"ARCHITECTURE_AND_ENGINEERING_GUIDE.md"
    text=path.read_text(encoding="utf-8");block=render()
    if START in text and END in text:
        before=text.split(START,1)[0].rstrip();after=text.split(END,1)[1].lstrip();text=before+"\n\n"+block+("\n\n"+after if after else "\n")
    else:text=text.rstrip()+"\n\n"+block+"\n"
    path.write_text(text,encoding="utf-8")

if __name__=="__main__":main()
