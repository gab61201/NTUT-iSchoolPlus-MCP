import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .constants import CPROG_BASE_URL

logger = logging.getLogger(__name__)


def _parse_matric_list(html: str) -> list[dict]:
    """Parse format=-2 page: year → matric (學制) list."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        m = re.search(r"matric=([^&]+)", href)
        if m:
            items.append({"matric": m.group(1), "name": a.get_text(strip=True)})
    return items


def _parse_division_list(html: str) -> list[dict]:
    """Parse format=-3 page: year+matric → division (系所) list with credit summary.
    
    Uses regex because the APS HTML has unclosed <td> tags that confuse BeautifulSoup.
    """
    # Find the <h3> heading to locate the right context
    heading_pattern = re.compile(r"<H3>(\d+)\s*學年度入學\s*(\S+)\s*學分數統計表</H3>")
    if not heading_pattern.search(html):
        return []

    # Each row: <tr><td>...<a href="...division=XXX">NAME</A> then 8 <td> numbers
    row_pattern = re.compile(
        r"<a\s+href=\"[^\"]*?Cprog\.jsp\?[^\"]*?division=([^\">&]+)[^\"]*\"[^>]*>(.*?)</A>\s*"
        r"(?:</td>|<td[^>]*>)\s*(\d+)\s*(?:</td>|<td[^>]*>)\s*(\d+)\s*"
        r"(?:</td>|<td[^>]*>)\s*(\d+)\s*(?:</td>|<td[^>]*>)\s*(\d+)\s*"
        r"(?:</td>|<td[^>]*>)\s*(\d+)\s*(?:</td>|<td[^>]*>)\s*(\d+)\s*"
        r"(?:</td>|<td[^>]*>)\s*(\d+)\s*(?:</td>|<td[^>]*>)\s*(\d+)",
        re.DOTALL,
    )

    items: list[dict] = []
    for m in row_pattern.finditer(html):
        items.append({
            "division": m.group(1),
            "name": re.sub(r"<[^>]+>", "", m.group(2)).strip(),
            "common_required": int(m.group(3)),
            "school_common": int(m.group(4)),
            "elective_common": int(m.group(5)),
            "major_required_gov": int(m.group(6)),
            "major_required_school": int(m.group(7)),
            "major_elective": int(m.group(8)),
            "cross_domain": int(m.group(9)),
            "min_credits": int(m.group(10)),
        })
    return items


def _parse_course_table(html: str) -> dict:
    """Parse format=-4 page: full course table + graduation rules.
    
    Uses regex block-splitting because the APS HTML has unclosed <td> tags.
    """
    # Extract title from <H3>
    title_match = re.search(r"<H3>(.+?)</H3>", html)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""

    # Find blocks that contain Curr.jsp links (each is one course row)
    blocks = re.split(r"(<tr>)", html)
    courses: list[dict] = []
    seen = set()

    for i, block in enumerate(blocks):
        if "Curr.jsp" not in block:
            continue
        # Reconstruct the <tr> block
        if i > 0 and blocks[i - 1] == "<tr>":
            row = blocks[i - 1] + block
        else:
            row = block

        # Extract <td> values without relying on closing tags
        tds = re.findall(r"<td[^>]*>(.*?)(?=<td|<tr|</tr|$)", row, re.DOTALL)
        if len(tds) < 10:
            continue

        code = re.sub(r"<[^>]+>", "", tds[3]).strip()
        if not code or not re.match(r"^[A-Za-z0-9]+$", code):
            continue
        if code in seen:
            continue
        seen.add(code)

        cat = re.sub(r"<[^>]+>", "", tds[2]).strip()
        name = re.sub(r"<[^>]+>", "", tds[4]).strip()
        note = re.sub(r"<[^>]+>", "", tds[9]).strip()
        stage = re.sub(r"<[^>]+>", "", tds[7]).strip()
        group = re.sub(r"<[^>]+>", "", tds[8]).strip()

        try:
            courses.append({
                "year": int(re.sub(r"<[^>]+>", "", tds[0]).strip()),
                "semester": int(re.sub(r"<[^>]+>", "", tds[1]).strip()),
                "category": cat,
                "code": code,
                "name": name,
                "credits": float(re.sub(r"<[^>]+>", "", tds[5]).strip()),
                "hours": int(re.sub(r"<[^>]+>", "", tds[6]).strip()),
                "stage": stage,
                "group": group,
                "note": note,
            })
        except (ValueError, IndexError):
            continue

    # Parse graduation rules from the font[color=blue] inside the second table
    rules: list[str] = []
    font_match = re.search(
        r"<font\s+color=blue>\s*1\.(.*?)</font>", html, re.DOTALL
    )
    if font_match:
        raw_rules = re.sub(r"<[^>]+>", "\n", "1." + font_match.group(1))
        rules = [line.strip() for line in raw_rules.split("\n") if line.strip()]

    summary: dict = {}
    if rules:
        text = " ".join(rules)
        for label, key in [("最低畢業學分", "min_credits"), ("共同必修", "common_required"),
                           ("專業必修", "major_required"), ("專業選修", "major_elective")]:
            m = re.search(rf"{label}[：:]\s*(\d+)", text)
            if m:
                summary[key] = int(m.group(1))
        m = re.search(r"跨域及自由選修\s*(\d+)", text)
        if m:
            summary["cross_domain"] = int(m.group(1))

    return {
        "title": title,
        "credit_summary": summary,
        "courses": courses,
        "rules": rules,
    }


async def fetch_graduation_standard(
    client: httpx.AsyncClient,
    year: int,
    matric: str = "",
    division: str = "",
) -> dict | None:
    """Fetch graduation standard from Cprog.jsp.

    - year only         → returns {"matric_list": [...]}
    - year + matric     → returns {"division_list": [...]}
    - year + matric + division → returns full course table + rules
    """
    base = CPROG_BASE_URL + "?year=" + str(year)

    if not matric:
        # Level 1: only year → matric list
        url = base + "&format=-2"
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return {"matric_list": _parse_matric_list(resp.text)}
        except Exception as e:
            logger.error(f"fetch_graduation_standard (matric): {e}")
            return None

    if not division:
        # Level 2: year + matric → division list
        url = f"{base}&matric={matric}&format=-3"
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return {"division_list": _parse_division_list(resp.text)}
        except Exception as e:
            logger.error(f"fetch_graduation_standard (division): {e}")
            return None

    # Level 3: year + matric + division → full course table
    url = f"{base}&matric={matric}&division={division}&format=-4"
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return _parse_course_table(resp.text)
    except Exception as e:
        logger.error(f"fetch_graduation_standard (course): {e}")
        return None
