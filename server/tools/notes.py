import json
import os
from datetime import datetime, timezone

from . import mcp


@mcp.tool()
async def get_course_note(seme: str, course_id: str, notes_dir: str) -> str:
    note_path = os.path.join(notes_dir, f"{seme}_{course_id}_note.json")
    if not os.path.exists(note_path):
        return json.dumps({"content": "", "note_path": note_path}, ensure_ascii=False)
    try:
        with open(note_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return json.dumps({"error": f"無法讀取筆記: {e}"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def set_course_note(seme: str, course_id: str, content: str, notes_dir: str) -> str:
    os.makedirs(notes_dir, exist_ok=True)
    note_path = os.path.join(notes_dir, f"{seme}_{course_id}_note.json")

    existing = {}
    if os.path.exists(note_path):
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "content": content,
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(note_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        return json.dumps({"error": f"無法寫入筆記: {e}"}, ensure_ascii=False)

    return json.dumps(data, ensure_ascii=False)
