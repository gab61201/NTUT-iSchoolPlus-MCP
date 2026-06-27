import json

from . import mcp
from ._helpers import _get_files_internal


@mcp.tool()
async def get_course_videos(seme: str, course_id: str) -> str:
    course = await _get_files_internal(seme, course_id)

    videos = [
        {
            "identifier": k,
            "text": v.get("text", ""),
        }
        for k, v in course.video_dict.items()
    ]
    return json.dumps(
        {"seme": seme, "course_id": course_id, "videos": videos, "count": len(videos)},
        ensure_ascii=False,
    )


@mcp.tool()
async def get_course_video_url(seme: str, course_id: str, identifier: str) -> str:
    course = await _get_files_internal(seme, course_id)
    await course.fetch_files()
    video_info = course.video_dict.get(identifier)
    if not video_info:
        return json.dumps({"error": f"找不到影片 {identifier}"}, ensure_ascii=False)

    url = await course.fetch_video(identifier)
    if not url:
        return json.dumps({"error": "無法取得影片串流網址"}, ensure_ascii=False)

    return json.dumps(
        {
            "identifier": identifier,
            "text": video_info.get("text", ""),
            "url": url,
        },
        ensure_ascii=False,
    )
