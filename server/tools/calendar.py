import json

from . import mcp, session  # noqa: F401 — imported for side effect
from nportal.calendar import fetch_calendar_events


@mcp.tool()
async def get_school_calendar() -> str:
    """取得北科大行事曆 (iCal feed)。不須登入。"""
    events = await fetch_calendar_events(session.scraper.session)
    if events is None:
        return json.dumps({"error": "無法取得行事曆"}, ensure_ascii=False)

    # Add index
    items = [{"index": i, **e} for i, e in enumerate(events)]

    return json.dumps({"events": items}, ensure_ascii=False)
