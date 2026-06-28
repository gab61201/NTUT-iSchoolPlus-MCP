# AGENTS.md

## Project identity

MCP server (FastMCP) that scrapes NTUT iSchool+ — courses, timetables, syllabi, files, videos, bulletins.

## Commands

```bash
uv sync                          # install dependencies
uv run mcp dev main.py           # run MCP Inspector for manual testing
uv run python main.py            # run the MCP server (for AI clients)
```

No lint, typecheck, or test commands are configured.

## Environment

Set these so `login()` works with no arguments:

```
NTUT_STUDENT_ID=學號
NTUT_PASSWORD=nportal密碼
```

## Architecture

```
server/tools/*.py   # 17 MCP tools (one module per domain)
nportal/            # core: scraper (httpx), session, course, constants
main.py             # entry point: just calls mcp.run()
```

Two separate `Course` dicts in `nportal/session.py`:
- `course_list[seme][course_id]` — parsed from timetable HTML (has valid syllabus/description URLs)
- `ischool_courses[seme][course_id]` — iSchool-only courses that are NOT in the main timetable

## Critical gotchas

### Login requires two OAuth flows

After nportal login, the scraper must SSO into both:
1. `aa_0010-oauth` → `aps.ntut.edu.tw` (course system)
2. `ischool_plus_oauth` → `istudy.ntut.edu.tw` (iSchool+)

Both are needed for full tool coverage. All tools except notes require prior login.

### Syllabus/description URLs come ONLY from timetable HTML

The timetable page (`Select.jsp?format=-2&code=...`) contains both `ShowSyllabus.jsp?snum=...&code=...` and `Curr.jsp?format=-2&code=...` in the course list table. **Do not construct these URLs manually.** iSchool-only courses (in `ischool_courses`) have no syllabus/description URLs — that is correct behavior, never add fallbacks.

### get_ischool_course_list may return empty

This tool iterates `ischool_courses` only. If all iSchool courses also appear in the main timetable, the result is legitimately empty. Do not treat this as a bug.

### iSchool course content requires per-course context request

Before fetching files, videos, or bulletins for any iSchool course, you must first GET `https://istudy.ntut.edu.tw/xmlapi/index.php?action=my-course-path-info&onlyProgress=0&descendant=1&cid={8-digit-cid}` for that specific course. This sets the session context — without it, subsequent requests (forum_ajax, SCORM, etc.) will fail or return wrong data. One course at a time; there is no batching.

### Single persistent httpx session

All requests share one `httpx.AsyncClient` with cookies and `follow_redirects=True`. Session state is preserved across tool calls until `logout()`.

### Notes are local JSON files

`get_course_note` / `set_course_note` read/write JSON files to disk at a caller-specified `notes_dir`. These are stored locally, not on the NTUT servers.

### School calendar is public (no login required)

`get_school_calendar` reads the NTUT Google Calendar iCal feed. It uses the shared httpx session but works without login. Summary text is UTF-8 and may appear garbled in some terminals — the data itself is correct.

## NTUT-iSchoolMate/

This directory is a separate desktop app (NiceGUI) and is **not part of the MCP server**. The MCP server is a ground-up reimplementation that shares the same scraping logic but is an independent codebase.
