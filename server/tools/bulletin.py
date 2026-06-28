import json

from . import mcp
from ._helpers import _ensure_file_context


@mcp.tool()
async def get_bulletin_list(seme: str, course_id: str) -> str:
    course = await _ensure_file_context(seme, course_id)
    data = await course.get_bulletin()
    if data is None:
        return json.dumps({"error": "無法取得公告列表"}, ensure_ascii=False)

    items = []
    for i, v in enumerate(data.values()):
        items.append({
            "index": i,
            "subject": v.get("subject", ""),
            "postdate": v.get("postdate", ""),
            "poster": v.get("realname", "").strip(),
        })

    return json.dumps(
        {"seme": seme, "course_id": course_id, "bulletins": items, "count": len(items)},
        ensure_ascii=False,
    )


@mcp.tool()
async def get_bulletin(seme: str, course_id: str, index: int) -> str:
    course = await _ensure_file_context(seme, course_id)
    bulletin = await course.get_bulletin()
    if bulletin is None:
        return json.dumps({"error": "無法取得公告列表"}, ensure_ascii=False)

    items = list(bulletin.values())
    if index < 0 or index >= len(items):
        return json.dumps(
            {"error": f"索引 {index} 超出範圍（共 {len(items)} 則公告）"},
            ensure_ascii=False,
        )

    item = items[index]
    nid = item["node"]
    replies = await course.get_bulletin_reply(nid)
    if replies is None:
        return json.dumps({"error": "無法取得公告回覆"}, ensure_ascii=False)

    return json.dumps({
        "seme": seme,
        "course_id": course_id,
        "index": index,
        "subject": item.get("subject", ""),
        "postdate": item.get("postdate", ""),
        "poster": item.get("realname", "").strip(),
        "content": item.get("postcontenttext", ""),
        "replies": replies,
    }, ensure_ascii=False)
