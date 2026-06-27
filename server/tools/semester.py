import json

from . import mcp, session
from ._helpers import _require_login


@mcp.tool()
async def get_semester_list() -> str:
    _require_login()
    result = await session.fetch_seme_list()
    if isinstance(result, str):
        return json.dumps({"error": result}, ensure_ascii=False)
    return json.dumps({"seme_list": result}, ensure_ascii=False)
