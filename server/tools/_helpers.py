from . import mcp, session


def _require_login():
    if not session.logged_in:
        raise RuntimeError("尚未登入，請先呼叫 login 工具")


async def _ensure_course(seme: str, course_id: str):
    _require_login()
    if seme not in session.course_list:
        await session.fetch_timetable(seme)

    course = session.get_any_course(seme, course_id)
    if not course:
        raise RuntimeError(f"找不到課程 {seme}/{course_id}")
    return course


async def _ensure_file_context(seme: str, course_id: str):
    """確保課程存在 + file_url 已設定（不 fetch files，避免 race）"""
    _require_login()
    if seme not in session.course_list:
        await session.fetch_timetable(seme)

    course = session.get_any_course(seme, course_id)
    if not course or not course.file_url:
        ok = await session.fetch_course_file_urls()
        if isinstance(ok, str):
            raise RuntimeError(ok)
        course = session.get_any_course(seme, course_id)
        if not course:
            raise RuntimeError(f"找不到課程 {seme}/{course_id}")
    return course


async def _get_files_internal(seme: str, course_id: str):
    course = await _ensure_file_context(seme, course_id)

    if not course.file_dict and not course.video_dict:
        ok = await course.fetch_files()
        if not ok:
            raise RuntimeError("無法取得課程檔案")

    return course
