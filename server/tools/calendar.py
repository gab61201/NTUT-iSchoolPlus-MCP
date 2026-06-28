import json
from datetime import date, datetime, timedelta, timezone

from . import mcp, session
from nportal.calendar import fetch_calendar_events

TZ = timezone(timedelta(hours=8))
ONE_YEAR = timedelta(days=365)


def _parse_date(s: str) -> date | None:
    """Parse YYYY-MM-DD string, return None on failure."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@mcp.tool()
async def get_school_calendar(from_date: str = "", to_date: str = "") -> str:
    """取得北科大行事曆 (iCal feed)。不須登入。

    不加參數時預設回傳今天起 12 個月內的事件。
    可指定 from_date / to_date 自訂範圍，格式 YYYY-MM-DD。
    """
    events = await fetch_calendar_events(session.scraper.session)
    if events is None:
        return json.dumps({"error": "無法取得行事曆"}, ensure_ascii=False)

    from_d = _parse_date(from_date) or date.today()
    to_d = _parse_date(to_date) or (from_d + ONE_YEAR)

    items: list[dict] = []
    for i, e in enumerate(events):
        start_str = e.get("start", "")
        if not start_str:
            continue
        try:
            start = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if from_d <= start <= to_d:
            items.append({"index": i, **e})

    return json.dumps({"events": items}, ensure_ascii=False)
