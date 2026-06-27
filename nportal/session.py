import re
from .course import Course
from .scraper import WebScraper
from .constants import ISCHOOL_FILE_BASE_URL


class SessionManager:
    def __init__(self) -> None:
        self.scraper = WebScraper()
        self._logged_in = False

        self.student_id = ""
        self.seme_list: list[str] = []
        self.course_list: dict[str, dict[str, Course]] = {}
        self.student_info: dict = {}

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    async def login(self, student_id: str, password: str) -> str:
        login_response_json = await self.scraper.login(student_id, password)
        if not isinstance(login_response_json, dict):
            return f"登入失敗，未知錯誤: {login_response_json}"

        login_success = login_response_json.get("success", False)
        if not login_success:
            return login_response_json.get("errorMsg", "登入失敗")

        self.student_id = student_id

        # 從登入回應 JSON 取得個人資訊
        await self._capture_student_info(login_response_json)

        if not await self.scraper.oauth("aa_0010-oauth"):
            return "課程系統驗證失敗"
        if not await self.scraper.oauth("ischool_plus_oauth"):
            return "i 學園驗證失敗"

        self._logged_in = True
        return ""

    async def logout(self) -> None:
        self._logged_in = False
        await self.scraper.close()
        self.scraper = WebScraper()
        self.seme_list.clear()
        self.course_list.clear()
        self.student_info.clear()
        self.student_id = ""

    async def fetch_seme_list(self) -> list[str] | str:
        if not self._logged_in:
            return "尚未登入"

        if self.seme_list:
            return self.seme_list

        html_text = await self.scraper.fetch_seme_list_html()
        if not html_text:
            return "無法取得學期列表"

        seme_info = re.findall(r"year=(\d{3})&sem=(\d)", html_text)
        for year, sem in seme_info:
            self.seme_list.append(year + sem)

        return self.seme_list

    async def fetch_timetable(self, seme: str) -> list[list] | str:
        if not self._logged_in:
            return "尚未登入"

        html_text = await self.scraper.fetch_seme_timetable_html(seme)
        if not html_text:
            return f"無法取得 {seme} 課表"

        title = ["節/星期", "一", "二", "三", "四", "五"]
        timetable = [title]
        for i in range(1, 10):
            timetable.append([str(i)] + [None] * 5)

        timetable_html = re.search(
            r"<table border=1>.+</table>", html_text, re.DOTALL
        )
        if not timetable_html:
            return "無法解析課表"

        timetable_html_text = timetable_html.group()  # type:ignore
        all_classes = re.findall(
            r"<tr>\s*<td>\d{6}.+?</tr>", timetable_html_text, re.DOTALL
        )

        self.course_list.setdefault(seme, {})

        for class_html in all_classes:
            course = Course(self.scraper)
            course.seme = seme

            course_id = re.search(r"<td>(\d{6})", class_html)
            if not course_id:
                continue
            course.id = course_id.group(1)

            credits = re.search(r"<td align=CENTER>(\d.\d)", class_html)
            if credits:
                course.credits = credits.group(1)

            course_info = re.search(
                r'<A href="Curr.jsp.format=-2&code=(.{7})">(.+?)</A>', class_html
            )
            if not course_info:
                continue

            description_url = (
                "https://aps.ntut.edu.tw/course/tw/Curr.jsp?format=-2&code="
                + course_info.group(1)
            )
            course.description_url = description_url
            course.name = course_info.group(2)

            syllabus_url = re.search(
                r"ShowSyllabus.jsp.snum=(\d{6})&code=(\d{5})", class_html
            )
            if syllabus_url:
                course.syllabus_url = (
                    "https://aps.ntut.edu.tw/course/tw/" + syllabus_url.group()
                )

            hour_list = class_html.split("<td>")[6:13]
            for i in range(7):
                if hour_list[i] != "\u3000":
                    hours = hour_list[i].split()
                    for h in hours:
                        try:
                            h_int = int(h)
                            timetable[h_int][i + 1] = course.name
                        except (ValueError, IndexError):
                            pass

            self.course_list[seme][course.id] = course

        return timetable

    async def fetch_course_file_urls(self) -> bool | str:
        if not self._logged_in:
            return "尚未登入"

        html_text = await self.scraper.fetch_course_list_html()
        if not html_text:
            return "無法取得 i 學園課程列表"

        course_list = re.findall(
            r'<option value="\d{8}">\d{4}_.+?_\d{6}</option>', html_text
        )
        if not course_list:
            return "無法解析 i 學園課程列表"

        for course_data in course_list:
            data = re.search(
                r'<option value="(\d{8})">(\d{4})_(.+?)_(\d{6})</option>', course_data
            )
            if not data:
                continue

            seme = data.group(2)
            course_id = data.group(4)
            course: Course | None = self.course_list.get(seme, {}).get(course_id)
            if course:
                course.file_url = ISCHOOL_FILE_BASE_URL + data.group(1)

        return True

    def get_course(self, seme: str, course_id: str) -> Course | None:
        return self.course_list.get(seme, {}).get(course_id)

    async def _capture_student_info(self, login_json: dict) -> None:
        """從登入回應 JSON 和 nportal 首頁取得個人資訊"""
        import re
        import logging

        logger = logging.getLogger(__name__)

        self.student_info = {}
        self.student_info["student_id"] = self.student_id

        # 優先從登入 API 回應 JSON 提取
        # nportal 常見欄位: givenName, userDn, userMail, userType, userRole
        for key in ("givenName", "userName", "name", "cname", "realName", "displayName"):
            if login_json.get(key) and str(login_json[key]).strip():
                self.student_info["name"] = str(login_json[key]).strip()
                break
        if not self.student_info.get("name") and login_json.get("userDn"):
            cn = re.search(r'cn=([^,]+)', str(login_json["userDn"]), re.IGNORECASE)
            if cn:
                self.student_info["name"] = cn.group(1)

        for key in ("userMail", "email", "mail"):
            if login_json.get(key):
                self.student_info["email"] = str(login_json[key])
                break
        for key in ("userType", "userRole"):
            if login_json.get(key):
                self.student_info["role"] = str(login_json[key])
                break

        # 若 JSON 沒提供足夠資訊，嘗試從 nportal 首頁 HTML 提取
        if not self.student_info.get("name") or not self.student_info.get("department"):
            html_text = await self.scraper.fetch_nportal_index()
            if html_text:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_text, "html.parser")

                if not self.student_info.get("name"):
                    welcome = re.search(r'歡迎[回來]*[，,\s]*([^\s<]{2,10})', html_text)
                    if welcome:
                        self.student_info["name"] = welcome.group(1)
                    else:
                        cn_name = re.search(r'姓名[：:\s]*([^\s<]{2,10})', html_text)
                        if cn_name:
                            self.student_info["name"] = cn_name.group(1)

                if not self.student_info.get("department"):
                    dept = re.search(r'(?:系所|系級|科系|部別)[：:\s]*([^\s<]{2,30})', html_text)
                    if dept:
                        self.student_info["department"] = dept.group(1)

        if not self.student_info:
            self.student_info = {"student_id": self.student_id}

    async def fetch_student_info(self) -> dict | str:
        if not self._logged_in:
            return "尚未登入"

        if self.student_info:
            return self.student_info

        return {"student_id": self.student_id, "error": "登入時無法取得個人資訊"}
