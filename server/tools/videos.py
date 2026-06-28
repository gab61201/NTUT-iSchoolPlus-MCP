import json

from . import mcp
from ._helpers import _extract_ext, _get_files_internal, _tick_to_iso


@mcp.tool()
async def get_course_asset_list(seme: str, course_id: str) -> str:
    course = await _get_files_internal(seme, course_id)

    files = [
        {
            "index": i,
            "text": v.get("text", ""),
            "filename": f"{v.get('text', '')}.{_extract_ext(v.get('href', ''))}",
            "time": _tick_to_iso(k),
        }
        for i, (k, v) in enumerate(course.file_dict.items())
    ]
    videos = [
        {
            "index": i,
            "text": v.get("text", ""),
            "time": _tick_to_iso(k),
        }
        for i, (k, v) in enumerate(course.video_dict.items())
    ]
    return json.dumps(
        {
            "seme": seme,
            "course_id": course_id,
            "files": files,
            "videos": videos,
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def get_course_video_url(seme: str, course_id: str, index: int) -> str:
    course = await _get_files_internal(seme, course_id)
    video_keys = list(course.video_dict.keys())
    if index < 0 or index >= len(video_keys):
        return json.dumps({"error": f"index {index} 超出範圍 (0~{len(video_keys)-1})"}, ensure_ascii=False)
    identifier = video_keys[index]
    video_info = course.video_dict.get(identifier)
    if not video_info:
        return json.dumps({"error": f"找不到影片 index {index}"}, ensure_ascii=False)

    url = await course.fetch_video(identifier)
    if not url:
        return json.dumps({"error": "無法取得影片串流網址"}, ensure_ascii=False)

    return json.dumps(
        {
            "text": video_info.get("text", ""),
            "url": url,
        },
        ensure_ascii=False,
    )
