import json

from . import mcp, session
from ._helpers import _require_login


@mcp.tool()
async def get_student_info() -> str:
    _require_login()
    result = await session.fetch_student_info()
    if isinstance(result, str):
        return json.dumps({"error": result}, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)
