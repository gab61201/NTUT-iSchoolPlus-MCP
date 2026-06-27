import json

from . import mcp
from ._helpers import _ensure_course


@mcp.tool()
async def get_course_syllabus(seme: str, course_id: str) -> str:
    course = await _ensure_course(seme, course_id)
    data = await course.fetch_syllabus()
    if not data:
        return json.dumps({"error": "無法取得課程大綱"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_course_description(seme: str, course_id: str) -> str:
    course = await _ensure_course(seme, course_id)
    data = await course.fetch_description()
    if not data:
        return json.dumps({"error": "無法取得課程簡介"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)
