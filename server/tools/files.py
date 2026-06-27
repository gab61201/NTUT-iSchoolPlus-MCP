import asyncio
import json
import logging
import os
import sys

from . import mcp
from ._helpers import _get_files_internal

logger = logging.getLogger("ntut-ischoolplus-mcp")


@mcp.tool()
async def get_course_files(seme: str, course_id: str) -> str:
    course = await _get_files_internal(seme, course_id)

    files = [
        {
            "identifier": k,
            "text": v.get("text", ""),
            "href": v.get("href", ""),
            "identifier_db": v.get("identifier_db", ""),
        }
        for k, v in course.file_dict.items()
    ]
    return json.dumps(
        {"seme": seme, "course_id": course_id, "files": files, "count": len(files)},
        ensure_ascii=False,
    )


@mcp.tool()
async def get_course_file_url(seme: str, course_id: str, identifier: str) -> str:
    course = await _get_files_internal(seme, course_id)
    file_info = course.file_dict.get(identifier)
    if not file_info:
        return json.dumps({"error": f"找不到檔案 {identifier}"}, ensure_ascii=False)

    href = file_info.get("href", "")
    if not href or href == "about:blank":
        return json.dumps({"error": "此檔案無下載連結"}, ensure_ascii=False)

    return json.dumps(
        {
            "identifier": identifier,
            "text": file_info.get("text", ""),
            "href": href,
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def download_course_file(seme: str, course_id: str, identifier: str, save_path: str) -> str:
    course = await _get_files_internal(seme, course_id)
    file_info = course.file_dict.get(identifier)
    if not file_info:
        return json.dumps({"error": f"找不到檔案 {identifier}"}, ensure_ascii=False)

    href = file_info.get("href", "")
    if not href or href == "about:blank":
        return json.dumps({"error": "此檔案無下載連結"}, ensure_ascii=False)

    save_dir = os.path.dirname(save_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    file_size = 0
    async with course.scraper.session.stream("GET", href) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            async for chunk in resp.aiter_bytes():
                f.write(chunk)
                file_size += len(chunk)

    return json.dumps(
        {
            "identifier": identifier,
            "text": file_info.get("text", ""),
            "saved_to": save_path,
            "size_bytes": file_size,
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def download_course_all_files(seme: str, course_id: str, save_dir: str) -> str:
    course = await _get_files_internal(seme, course_id)
    if not course.file_dict:
        return json.dumps({"error": "此課程無檔案可下載"}, ensure_ascii=False)

    os.makedirs(save_dir, exist_ok=True)

    history_path = os.path.join(save_dir, f"{course.name}_{course.id}_downloads.json")
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
    for identifier, file_info in course.file_dict.items():
        if identifier in downloaded_ids:
            skipped_files.append({"identifier": identifier, "text": file_info.get("text", "")})
            continue
        href = file_info.get("href", "")
        if not href or href == "about:blank":
            skipped_files.append({"identifier": identifier, "text": file_info.get("text", ""), "reason": "無下載連結"})
            continue
        files_to_download.append((identifier, file_info))

    total = len(files_to_download)
    if total == 0:
        return json.dumps(
            {
                "course": course.name,
                "course_id": course_id,
                "seme": seme,
                "summary": "所有檔案已下載過或無有效連結",
                "total_downloadable": 0,
                "saved": [],
                "skipped": skipped_files,
                "failed": [],
            },
            ensure_ascii=False,
        )

    print(f"[download_course_all_files] {course.name}: {total} 個檔案待下載", file=sys.stderr)
    logger.info("download_course_all_files: %s: %d files to download", course.name, total)

    saved_files = []
    failed_files = []
    new_identifiers = []

    for idx, (identifier, file_info) in enumerate(files_to_download, 1):
        href = file_info["href"]
        text = file_info.get("text", identifier)

        if href.startswith("https://istudy.ntut.edu.tw/"):
            ext = href.rsplit(".", 1)[-1].rsplit("?", 1)[0]
            if len(ext) > 10 or "/" in ext:
                ext = "html"
        else:
            ext = "html"
        filename = f"{text}.{ext}"
        filepath = os.path.join(save_dir, filename)

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
            saved_files.append({"identifier": identifier, "text": text, "path": filepath})
            new_identifiers.append(identifier)
            print(f"[download_course_all_files] [{idx}/{total}] OK: {text}", file=sys.stderr)
            logger.info("download_course_all_files: [%d/%d] OK: %s", idx, total, text)
        else:
            failed_files.append({"identifier": identifier, "text": text, "error": last_error})
            print(f"[download_course_all_files] [{idx}/{total}] FAIL: {text} — {last_error}", file=sys.stderr)
            logger.warning("download_course_all_files: [%d/%d] FAIL: %s — %s", idx, total, text, last_error)

    downloaded_ids.update(new_identifiers)
    history["identifiers"] = sorted(downloaded_ids)
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return json.dumps(
        {
            "course": course.name,
            "course_id": course_id,
            "seme": seme,
            "save_dir": save_dir,
            "total_downloadable": total,
            "saved_count": len(saved_files),
            "skipped_count": len(skipped_files),
            "failed_count": len(failed_files),
            "saved": saved_files,
            "skipped": skipped_files,
            "failed": failed_files,
        },
        ensure_ascii=False,
    )
