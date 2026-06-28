import asyncio
import json
import logging
import os
import sys

from . import mcp, session
from ._helpers import _ensure_timetable, _extract_ext, _get_files_internal, _require_login

logger = logging.getLogger("ntut-ischoolplus-mcp")


async def _download_single_file(course, identifier: str, save_path: str) -> dict:
    file_info = course.file_dict.get(identifier)
    if not file_info:
        return {"error": f"找不到檔案 {identifier}"}

    href = file_info.get("href", "")
    if not href or href == "about:blank":
        return {"error": "此檔案無下載連結"}

    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    last_error = ""
    for attempt in range(1, 4):
        try:
            file_size = 0
            async with course.scraper.session.stream("GET", href) as resp:
                resp.raise_for_status()
                with open(save_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
                        file_size += len(chunk)
            return {
                "text": file_info.get("text", ""),
                "saved_to": save_path,
                "size_bytes": file_size,
            }
        except Exception as e:
            last_error = str(e)
            if attempt < 3:
                await asyncio.sleep(2 ** (attempt - 1))

    return {"error": f"下載失敗（已重試 3 次）: {last_error}"}


async def _download_all_files(course, save_dir: str) -> dict:
    if not course.file_dict:
        return {"summary": "此課程無檔案可下載", "saved": [], "skipped": [], "failed": []}

    os.makedirs(save_dir, exist_ok=True)

    history_path = os.path.join(save_dir, "_downloads.json")
    history = {}
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    downloaded_ids = set(history.get("identifiers", []))

    files_to_download = []
    skipped_files = []
    for fid, fi in course.file_dict.items():
        entry = {"text": fi.get("text", "")}
        if fid in downloaded_ids:
            skipped_files.append(entry)
            continue
        href = fi.get("href", "")
        if not href or href == "about:blank":
            entry["reason"] = "無下載連結"
            skipped_files.append(entry)
            continue
        files_to_download.append((fid, fi))

    total = len(files_to_download)
    if total == 0:
        return {
            "summary": "所有檔案已下載過或無有效連結",
            "saved": [],
            "skipped": skipped_files,
            "failed": [],
        }

    print(f"[ischool_file_download] {course.name}: {total} 個檔案待下載", file=sys.stderr)
    logger.info("ischool_file_download: %s: %d files to download", course.name, total)

    saved_files = []
    failed_files = []
    new_identifiers = []

    for idx, (fid, fi) in enumerate(files_to_download, 1):
        href = fi["href"]
        text = fi.get("text", fid)
        filename = f"{text}.{_extract_ext(href)}"
        filepath = os.path.join(save_dir, filename.replace("/", "_").replace("\\", "_"))

        success = False
        last_error = ""
        for attempt in range(1, 4):
            try:
                async with course.scraper.session.stream("GET", href) as resp:
                    resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
                success = True
                break
            except Exception as e:
                last_error = str(e)
                if attempt < 3:
                    await asyncio.sleep(2 ** (attempt - 1))

        if success:
            saved_files.append({"text": text, "path": filepath})
            new_identifiers.append(fid)
            print(f"[ischool_file_download] [{idx}/{total}] OK: {text}", file=sys.stderr)
            logger.info("ischool_file_download: [%d/%d] OK: %s", idx, total, text)
        else:
            failed_files.append({"text": text, "error": last_error})
            print(f"[ischool_file_download] [{idx}/{total}] FAIL: {text} — {last_error}", file=sys.stderr)
            logger.warning("ischool_file_download: [%d/%d] FAIL: %s — %s", idx, total, text, last_error)

    downloaded_ids.update(new_identifiers)
    history["identifiers"] = sorted(downloaded_ids)
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return {
        "summary": f"{len(saved_files)} ok, {len(skipped_files)} skipped, {len(failed_files)} failed",
        "saved": saved_files,
        "skipped": skipped_files,
        "failed": failed_files,
    }


@mcp.tool()
async def ischool_file_download(
    save_path: str,
    seme: str = "",
    course_id: str = "",
    index: int = -1,
) -> str:
    _require_login()

    # --- input validation ---
    if not seme and course_id:
        return json.dumps({"error": "指定 course_id 時必須同時指定 seme"}, ensure_ascii=False)
    if index >= 0 and not course_id:
        return json.dumps({"error": "指定 index 時必須同時指定 course_id"}, ensure_ascii=False)

    # --- single file ---
    if seme and course_id and index >= 0:
        course = await _get_files_internal(seme, course_id)
        file_keys = list(course.file_dict.keys())
        if index >= len(file_keys):
            return json.dumps({"error": f"index {index} 超出範圍 (0~{len(file_keys)-1})"}, ensure_ascii=False)
        identifier = file_keys[index]
        result = await _download_single_file(course, identifier, save_path)
        return json.dumps(result, ensure_ascii=False)

    # --- single course, all files ---
    if seme and course_id:
        course = await _get_files_internal(seme, course_id)
        dirname = f"{course.name}_{course.id}".replace("/", "_").replace("\\", "_")
        save_dir = os.path.join(save_path, dirname)
        result = await _download_all_files(course, save_dir)
        return json.dumps({
            "seme": seme, "course_id": course_id, "course": course.name,
            "save_dir": save_dir, **result,
        }, ensure_ascii=False)

    # --- multiple courses (one seme or all semesters) ---
    semesters = [seme] if seme else session.seme_list
    if not semesters:
        r = await session.fetch_seme_list()
        if isinstance(r, str):
            return json.dumps({"error": r}, ensure_ascii=False)
        semesters = session.seme_list
    if not semesters:
        return json.dumps({"error": "無法取得學期列表"}, ensure_ascii=False)

    all_results = {}
    total_stats = {"saved": 0, "skipped": 0, "failed": 0, "courses": 0, "courses_no_files": 0}

    for s in semesters:
        await _ensure_timetable(s)

        ok = await session.fetch_course_file_urls()
        if isinstance(ok, str):
            all_results[s] = {"error": ok}
            continue

        # collect courses (main timetable + iSchool-only)
        courses = {}
        courses.update(session.course_list.get(s, {}))
        courses.update(session.ischool_courses.get(s, {}))

        seme_results = {}
        for cid, course in courses.items():
            if not course.file_url:
                seme_results[cid] = {"error": "此課程無 i 學園檔案"}
                total_stats["courses_no_files"] += 1
                continue

            if not course.file_dict and not course.video_dict:
                if not await course.fetch_files():
                    seme_results[cid] = {"error": "無法取得課程檔案"}
                    total_stats["courses_no_files"] += 1
                    continue

            if not course.file_dict:
                continue

            dirname = f"{course.name}_{cid}".replace("/", "_").replace("\\", "_")
            save_dir = os.path.join(save_path, s, dirname)
            dr = await _download_all_files(course, save_dir)
            seme_results[cid] = {"course": course.name, "save_dir": save_dir, **dr}
            total_stats["saved"] += len(dr.get("saved", []))
            total_stats["skipped"] += len(dr.get("skipped", []))
            total_stats["failed"] += len(dr.get("failed", []))
            total_stats["courses"] += 1

        all_results[s] = seme_results

    return json.dumps({"results": all_results, "stats": total_stats}, ensure_ascii=False)
