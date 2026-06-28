import json

from . import mcp
from ._helpers import _ensure_file_context


@mcp.tool()
async def get_course_homework_list(seme: str, course_id: str) -> str:
    course = await _ensure_file_context(seme, course_id)
    data = await course.fetch_homework_list()
    if data is None:
        return json.dumps({"error": "無法取得作業/報告列表"}, ensure_ascii=False)

    items = [
        {
            "index": i,
            "name": v.get("name", ""),
            "type": v.get("type", ""),
            "status": v.get("status", ""),
            "deadline": v.get("deadline", ""),
            "percent": v.get("percent", ""),
            "exhibit": v.get("exhibit", ""),
            "has_peer_review": v.get("has_peer_review", False),
        }
        for i, v in enumerate(data)
    ]

    return json.dumps(
        {"homeworks": items},
        ensure_ascii=False,
    )
