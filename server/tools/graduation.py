import json

from . import mcp, session
from nportal.graduation import fetch_graduation_standard


@mcp.tool()
async def get_graduation_standard(year: int, matric: str = "", division: str = "") -> str:
    """取得課程標準（畢業科目表）。

    依參數數量決定回傳層級：
      year only          → matric (學制) 列表
      year + matric      → division (系所) 列表（含學分統計）
      year + matric + division → 完整課程科目表 + 畢業門檻

    matric 值: 7=四技, 6=二技, 8=碩士班, 9=博士班, 5=五專, A=碩士在職班, D=EMBA, F=進修部四技, G=第二專長, H=微學程, 1=學程
    """
    data = await fetch_graduation_standard(
        session.scraper.session,
        year=year,
        matric=matric,
        division=division,
    )
    if data is None:
        return json.dumps({"error": "無法取得課程標準"}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)
