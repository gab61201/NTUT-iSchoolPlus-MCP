import json

from . import mcp
from ._helpers import _ensure_file_context


@mcp.tool()
async def get_bulletin_list(seme: str, course_id: str) -> str:
    course = await _ensure_file_context(seme, course_id)
    data = await course.get_bulletin()
    if data is None:
        return json.dumps({"error": "無法取得公告列表"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_bulletin_reply(seme: str, course_id: str, nid: str) -> str:
    course = await _ensure_file_context(seme, course_id)
    data = await course.get_bulletin_reply(nid)
    if data is None:
        return json.dumps({"error": "無法取得公告回覆"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_bulletin_reply_by_index(seme: str, course_id: str, index: int) -> str:
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

    nid = items[index]["node"]
    data = await course.get_bulletin_reply(nid)
    if data is None:
        return json.dumps({"error": "無法取得公告回覆"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)
