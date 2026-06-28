import json

from . import mcp, session
from ._helpers import _ensure_timetable, _require_login


@mcp.tool()
async def get_timetable(seme: str) -> str:
    _require_login()
    result = await session.fetch_timetable(seme)
    if isinstance(result, str):
        return json.dumps({"error": result}, ensure_ascii=False)
    return json.dumps({"timetable": result}, ensure_ascii=False, default=str)


@mcp.tool()
async def get_course_list(seme: str) -> str:
    _require_login()
    await _ensure_timetable(seme)

    courses = []
    total = 0.0
    for c in session.course_list.get(seme, {}).values():
        courses.append({"course_id": c.id, "name": c.name, "credits": c.credits, "status": c.status})
        try:
            total += float(c.credits)
        except (ValueError, TypeError):
            pass
    return json.dumps(
        {"courses": courses, "count": len(courses), "total_credits": total},
        ensure_ascii=False,
    )


@mcp.tool()
async def get_ischool_course_list(seme: str) -> str:
    _require_login()
    await _ensure_timetable(seme)

    ok = await session.fetch_course_file_urls()
    if isinstance(ok, str):
        return json.dumps({"error": ok}, ensure_ascii=False)

    timetable_courses = session.course_list.get(seme, {})
    courses = []
    for course in session.ischool_courses.get(seme, {}).values():
        tc = timetable_courses.get(course.id)
        status = tc.status if tc else "退選"
        courses.append({
            "course_id": course.id,
            "name": course.name,
            "status": status,
        })
    return json.dumps(
        {"courses": courses, "count": len(courses)},
        ensure_ascii=False,
    )
