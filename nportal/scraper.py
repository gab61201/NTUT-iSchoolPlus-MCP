import logging
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from typing import Literal

from bs4 import BeautifulSoup
import httpx
from httpx import Response

from .constants import *

urllib3.disable_warnings(InsecureRequestWarning)


class WebScraper:

    def __init__(self) -> None:
        headers = {
            "User-Agent": "Direk android App",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.session = httpx.AsyncClient(
            verify=False,
            headers=headers,
            follow_redirects=True,
            timeout=None,
        )
        self.student_id = ""

    async def login(self, student_id: str, password: str) -> dict | None:
        self.session.headers.update({"Referer": NPORTAL_LOGIN_PAGE_URL})

        try:
            post_data = {
                "muid": student_id,
                "mpassword": password,
                "forceMobile": "mobile",
            }
            login_response = await self.session.post(
                NPORTAL_LOGIN_URL, data=post_data, timeout=10
            )
            login_response.raise_for_status()
            self.student_id = student_id
            return login_response.json()

        except Exception as e:
            logging.error(f"web_scraper.login error:\n{e}")
            return None

        finally:
            self.session.headers.pop("Referer", None)

    async def oauth(
        self, apOu: Literal["aa_0010-oauth", "ischool_plus_oauth"]
    ) -> bool:
        initial_oath_url = OAUTH_BASE_URL + apOu
        logging.info(f"正在執行 SSO 流程，目標: {apOu}")
        self.session.headers.update({"Referer": NPORTAL_LOGIN_PAGE_URL})

        try:
            oath_page_response = await self.session.get(initial_oath_url, timeout=10)
            oath_page_response.raise_for_status()

            soup = BeautifulSoup(oath_page_response.text, "html.parser")
            inputs = soup.select("form[name='ssoForm'] input")
            if not inputs:
                logging.error("SSO 流程失敗：在 'ssoForm' 表單中找不到任何 <input> 標籤。")
                return False

            course_oath_data = {
                str(item.get("name")): item.get("value") for item in inputs
            }
            logging.debug("成功解析到 SSO 表單資料")

            self.session.headers.update({"Referer": initial_oath_url})
            logging.debug(f"正在向 {SSO_POST_URL} 提交 SSO 表單...")

            sso_post_response = await self.session.post(
                SSO_POST_URL,
                data=course_oath_data,
                follow_redirects=False,
                timeout=15,
            )
            if not sso_post_response.is_redirect:
                sso_post_response.raise_for_status()

            redirect_url = sso_post_response.headers.get("Location")
            if not redirect_url:
                logging.error(
                    "SSO 流程失敗：伺服器 POST 回應中未包含 'Location' 重導向標頭。"
                )
                return False

            logging.info(f"取得 SSO 重導向網址: {redirect_url}")
            final_response = await self.session.get(
                redirect_url, follow_redirects=False, timeout=10
            )
            if not final_response.is_redirect:
                final_response.raise_for_status()

            logging.info(f"SSO 流程成功完成，已取得 {apOu} 的 session。")
            return True

        except Exception as e:
            logging.error(f"WebScraper.oauth({apOu} error:\n{e})")
            return False

        finally:
            self.session.headers.pop("Referer", None)

    async def fetch_seme_list_html(self) -> str | None:
        URL = "https://aps.ntut.edu.tw/course/tw/Select.jsp"
        try:
            logging.debug(f"正在請求 URL: {URL}")
            response = await self.session.get(URL, timeout=10)
            response.raise_for_status()
            logging.info("成功獲取學年學期列表頁面。")
            return response.text

        except httpx.TimeoutException:
            logging.error(f"請求超時: {URL}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP 狀態碼錯誤: {e.response.status_code} {e.response.reason_phrase} "
                f"在請求 URL: {e.request.url}"
            )
            return None
        except httpx.RequestError as e:
            logging.error(f"發生網路請求錯誤: {e.__class__.__name__} - {e}")
            return None
        except Exception as e:
            logging.critical(f"抓取學年學期列表時發生未預期的嚴重錯誤: {e}", exc_info=True)
            return None

    async def fetch_seme_timetable_html(self, seme: str) -> str | None:
        timetable_url = (
            f"https://aps.ntut.edu.tw/course/tw/Select.jsp"
            f"?format=-2&code={self.student_id}&year={seme[:3]}&sem={seme[-1]}"
        )
        try:
            response = await self.session.get(timetable_url, timeout=10)
            response.raise_for_status()
            logging.info(f"成功獲取{seme}課程列表頁面。")
            return response.text

        except httpx.TimeoutException:
            logging.error(f"請求超時: {timetable_url}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP 狀態碼錯誤: {e.response.status_code} {e.response.reason_phrase} "
                f"在請求 URL: {e.request.url}"
            )
            return None
        except httpx.RequestError as e:
            logging.error(f"發生網路請求錯誤: {e.__class__.__name__} - {e}")
            return None
        except Exception as e:
            logging.critical(f"抓取{seme}課程列表時發生未預期的嚴重錯誤: {e}", exc_info=True)
            return None

    async def fetch_course_list_html(self) -> str | None:
        try:
            response = await self.session.get(ISCHOOL_COURSE_LIST_URL, timeout=10)
            response.raise_for_status()
            logging.info(f"成功獲取ischool課程列表頁面。")
            return response.text

        except httpx.TimeoutException:
            logging.error(f"請求超時: {ISCHOOL_COURSE_LIST_URL}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP 狀態碼錯誤: {e.response.status_code} {e.response.reason_phrase} "
                f"在請求 URL: {e.request.url}"
            )
            return None
        except httpx.RequestError as e:
            logging.error(f"發生網路請求錯誤: {e.__class__.__name__} - {e}")
            return None
        except Exception as e:
            logging.critical(f"抓取ischool課程列表時發生未預期的嚴重錯誤: {e}", exc_info=True)
            return None

    async def get(self, url: str) -> Response | None:
        try:
            response = await self.session.get(url, timeout=10)
            response.raise_for_status()
            logging.info(f"成功獲取{url}")
            return response

        except httpx.TimeoutException:
            logging.error(f"請求超時: {url}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP 狀態碼錯誤: {e.response.status_code} {e.response.reason_phrase} "
                f"在請求 URL: {e.request.url}"
            )
            return None
        except httpx.RequestError as e:
            logging.error(f"發生網路請求錯誤: {e.__class__.__name__} - {e}")
            return None
        except Exception as e:
            logging.critical(f"抓取{url}時發生未預期的嚴重錯誤: {e}", exc_info=True)
            return None

    async def close(self) -> None:
        await self.session.aclose()

    async def fetch_nportal_index(self) -> str | None:
        try:
            response = await self.session.get(NPORTAL_INDEX_URL, timeout=10)
            response.raise_for_status()
            logging.info("成功獲取 nportal 首頁")
            return response.text
        except httpx.TimeoutException:
            logging.error(f"請求超時: {NPORTAL_INDEX_URL}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP 狀態碼錯誤: {e.response.status_code} "
                f"在請求 URL: {e.request.url}"
            )
            return None
        except httpx.RequestError as e:
            logging.error(f"發生網路請求錯誤: {e.__class__.__name__} - {e}")
            return None
        except Exception as e:
            logging.critical(f"抓取 nportal 首頁時發生未預期的嚴重錯誤: {e}", exc_info=True)
            return None
