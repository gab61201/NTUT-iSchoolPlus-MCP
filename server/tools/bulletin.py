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
        {"bulletins": items},
        ensure_ascii=False,
    )


@mcp.tool()
async def get_bulletin(seme: str, course_id: str, index: int) -> str:
    course = await _ensure_file_context(seme, course_id)
    bulletin = await course.get_bulletin()
    if bulletin is None:
        return json.dumps({"error": "無法取得公告列表"}, ensure_ascii=False)

    items = list(bulletin.items())
    if index < 0 or index >= len(items):
        return json.dumps(
            {"error": f"索引 {index} 超出範圍（共 {len(items)} 則公告）"},
            ensure_ascii=False,
        )

    _compound_key, item = items[index]
    boardid = item["boardid"]
    node = item["node"]

    # NTUT-iSchoolMate: nid 傳 node，回應用 f"{boardid}|{node}" 查
    raw = await course.get_bulletin_reply(node)

    def _make_reply(v: dict) -> dict:
        r = {
            "realname": v.get("realname", "").strip(),
            "poster": v.get("poster", ""),
            "postdate": v.get("postdate", ""),
            "content": v.get("postcontenttext", ""),
        }
        return r

    async def _parse_replies(parent_node: str) -> list:
        """遞迴解析 reply + whisper"""
        thread = raw.get(f"{boardid}|{parent_node}") if raw else None
        if not thread or not thread.get("data"):
            return []
        result = []
        for v in thread["data"].values():
            reply = _make_reply(v)
            reply_node = v.get("node", "")
            # whisper
            w_raw = await course.get_bulletin_whisper(reply_node)
            if w_raw:
                wr = w_raw.get(f"{boardid}|{reply_node}")
                if wr and isinstance(wr, list):
                    reply["comments"] = [
                        {"realname": w.get("creator_realname", "").strip(),
                         "poster": w.get("creator", ""),
                         "create_time": w.get("create_time", ""),
                         "content": w.get("content", "")}
                        for w in wr
                    ]
            # sub-replies (replies to this reply)
            sub = await _parse_replies(reply_node) if raw.get(f"{boardid}|{reply_node}") else []
            if sub:
                reply["replies"] = sub
            result.append(reply)
        return result

    replies = await _parse_replies(node) if raw else []

    result = {
        "subject": item.get("subject", ""),
        "postdate": item.get("postdate", ""),
        "poster": item.get("realname", "").strip(),
        "content": item.get("postcontenttext", ""),
    }
    if replies:
        result["replies"] = replies
    return json.dumps(result, ensure_ascii=False)
