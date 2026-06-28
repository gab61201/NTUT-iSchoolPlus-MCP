from datetime import datetime, timedelta, timezone

from . import mcp, session


def _extract_ext(href: str) -> str:
    if href.startswith("https://istudy.ntut.edu.tw/"):
        ext = href.rsplit(".", 1)[-1].rsplit("?", 1)[0]
        if len(ext) > 10 or "/" in ext:
            return "html"
        return ext
    return "html"


def _tick_to_iso(identifier: str) -> str:
    parts = identifier.rsplit("_", 1)
    if len(parts) == 2:
        try:
            tick_us = int(parts[1])
            dt = datetime.fromtimestamp(tick_us / 1_000_000, tz=timezone(timedelta(hours=8)))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return ""
    return ""


def _require_login():
    if not session.logged_in:
        raise RuntimeError("尚未登入，請先呼叫 login 工具")


async def _ensure_timetable(seme: str) -> None:
    if seme not in session.course_list:
        r = await session.fetch_timetable(seme)
        if isinstance(r, str):
            raise RuntimeError(r)


async def _ensure_course(seme: str, course_id: str):
    _require_login()
    await _ensure_timetable(seme)

    course = session.get_any_course(seme, course_id)
    if not course:
        raise RuntimeError(f"找不到課程 {seme}/{course_id}")
    return course


async def _ensure_file_context(seme: str, course_id: str):
    """確保課程存在 + file_url 已設定（不 fetch files，避免 race）"""
    _require_login()
    await _ensure_timetable(seme)

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
            raise RuntimeError(f"無法取得課程檔案 {seme}/{course_id}")

    return course
