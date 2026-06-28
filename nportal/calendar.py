import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

ICAL_URL = "https://calendar.google.com/calendar/ical/docfuhim9b22fqvp2tk842ak3c%40group.calendar.google.com/public/basic.ics"
TZ = timezone(timedelta(hours=8))

# Patterns
_RE_VEVENT = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.DOTALL)
_RE_DTSTART = re.compile(r"^DTSTART(?:;VALUE=DATE)?:(.+)$", re.MULTILINE)
_RE_DTEND = re.compile(r"^DTEND(?:;VALUE=DATE)?:(.+)$", re.MULTILINE)
_RE_SUMMARY = re.compile(r"^SUMMARY:(.+)$", re.MULTILINE)
_RE_DESC = re.compile(r"^DESCRIPTION:(.+)", re.MULTILINE)
_RE_LOC = re.compile(r"^LOCATION:(.+)", re.MULTILINE)


def _get_field(block: str, pattern: re.Pattern) -> str | None:
    m = pattern.search(block)
    if not m:
        return None
    return _decode_ical_text(m.group(1).strip())


def _parse_dt(raw: str) -> datetime | None:
    """Parse iCal DT value. All-day: YYYYMMDD, datetime: YYYYMMDDTHHMMSS(Z)"""
    raw = raw.strip()
    if not raw:
        return None
    is_utc = raw.endswith("Z")
    clean = raw.rstrip("Z")
    if len(clean) == 8:  # all-day date
        dt = datetime.strptime(clean, "%Y%m%d")
        return dt.replace(tzinfo=TZ)
    try:
        dt = datetime.strptime(clean, "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    if is_utc:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(TZ)
    else:
        dt = dt.replace(tzinfo=TZ)
    return dt


def _decode_ical_text(text: str) -> str:
    text = text.replace("\\n", "\n").replace("\\;", ";").replace("\\\\", "\\")
    return text


async def fetch_calendar_events(
    client: httpx.AsyncClient | None = None,
) -> list[dict] | None:
    """Fetch and parse the NTUT school calendar iCal feed.

    Returns list of events sorted by start date, newest first. Each event:
      { "summary", "start" (ISO fmt), "end" (ISO fmt),
        "location" (optional), "description" (optional) }
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30)
        close_client = True

    try:
        response = await client.get(ICAL_URL)
        response.raise_for_status()
        raw = response.text
    except Exception as e:
        logging.error(f"fetch_calendar_events error: {e}")
        return None
    finally:
        if close_client:
            await client.aclose()

    events: list[dict] = []
    for match in _RE_VEVENT.finditer(raw):
        block = match.group(1)

        dtstart_match = _RE_DTSTART.search(block)
        dtend_match = _RE_DTEND.search(block)
        summary_match = _RE_SUMMARY.search(block)
        desc_match = _RE_DESC.search(block)
        loc_match = _RE_LOC.search(block)

        if not summary_match:
            continue

        summary = _decode_ical_text(summary_match.group(1).strip())
        event: dict = {"summary": summary}

        if dtstart_match:
            start = _parse_dt(dtstart_match.group(1))
            if start:
                event["start"] = start.strftime("%Y-%m-%d %H:%M:%S")

        if dtend_match:
            end = _parse_dt(dtend_match.group(1))
            if end:
                event["end"] = end.strftime("%Y-%m-%d %H:%M:%S")

        if loc_match:
            loc = _decode_ical_text(loc_match.group(1).strip())
            event["location"] = loc

        if desc_match:
            desc = _decode_ical_text(desc_match.group(1).strip())
            event["description"] = desc

        events.append(event)

    events.sort(key=lambda e: e.get("start", ""), reverse=True)
    return events
