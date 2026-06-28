import json
import os

from . import mcp, session
from ._helpers import _require_login


@mcp.tool()
async def login(student_id: str = "", password: str = "") -> str:
    if not student_id:
        student_id = os.environ.get("NTUT_STUDENT_ID", "")
    if not password:
        password = os.environ.get("NTUT_PASSWORD", "")

    if not student_id or not password:
        return json.dumps(
            {"error": "請傳入帳密，或設定 NTUT_STUDENT_ID / NTUT_PASSWORD 環境變數"},
            ensure_ascii=False,
        )

    err = await session.login(student_id, password)
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)
    return json.dumps(
        {"success": True, "student_id": session.student_id, **session.student_info},
        ensure_ascii=False,
    )


@mcp.tool()
async def logout() -> str:
    await session.logout()
    return json.dumps({"success": True}, ensure_ascii=False)
