# NTUT iSchoolPlus MCP

[![GitHub](https://img.shields.io/badge/github-gab61201/NTUT--iSchoolPlus--MCP-blue)](https://github.com/gab61201/NTUT-iSchoolPlus-MCP)

MCP (Model Context Protocol) server for NTUT iSchool+ — 讓 AI 幫你查課表、大綱、檔案、公告。

## 安裝

需要 Python ≥3.11 + [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/gab61201/NTUT-iSchoolPlus-MCP.git
cd NTUT-iSchoolPlus-MCP
uv sync
```

## 使用方式

### 1. MCP Inspector 測試

```bash
export NTUT_STUDENT_ID=你的學號
export NTUT_PASSWORD=你的密碼
uv run mcp dev main.py
```

瀏覽器會自動打開 `http://localhost:6274`，可在 Web GUI 中逐一測試所有 tools。

### 2. 接入 Claude Desktop

在 `claude_desktop_config.json` 加入：

```json
{
  "mcpServers": {
    "ntut-ischoolplus": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/NTUT-iSchoolPlus-MCP", "python", "main.py"],
      "env": {
        "NTUT_STUDENT_ID": "你的學號",
        "NTUT_PASSWORD": "你的密碼"
      }
    }
  }
}
```

### 3. 接入 OpenCode

在 `opencode.json` 加入（含環境變數，`login()` 免傳參數）：

```json
{
  "mcp": {
    "ntut-ischoolplus": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/NTUT-iSchoolPlus-MCP", "python", "main.py"],
      "environment": {
        "NTUT_STUDENT_ID": "你的學號",
        "NTUT_PASSWORD": "你的密碼"
      },
      "enabled": true
    }
  }
}
```

### 4. 接入 Hermes Agent

在 `~/.hermes/config.yaml` 加入：

```yaml
mcp_servers:
  ntut-ischoolplus:
    command: "uv"
    args: ["run", "--directory", "/path/to/NTUT-iSchoolPlus-MCP", "python", "main.py"]
    environment:
      NTUT_STUDENT_ID: "你的學號"
      NTUT_PASSWORD: "你的密碼"
```

工具在 Hermes 中會自動加上前綴，例如 `mcp_ntut-ischoolplus_login`。啟動 `hermes chat` 後即可使用。

### 5. 接入 OpenClaw

在 `~/.openclaw/openclaw.json` (JSON5) 加入：

```json5
{
  mcp: {
    "ntut-ischoolplus": {
      command: ["uv", "run", "--directory", "/path/to/NTUT-iSchoolPlus-MCP", "python", "main.py"],
      environment: {
        NTUT_STUDENT_ID: "你的學號",
        NTUT_PASSWORD: "你的密碼",
      },
    },
  },
}
```

OpenClaw 支援 config hot reload，修改後無需重啟。

## 環境變數

| 變數 | 說明 |
|------|------|
| `NTUT_STUDENT_ID` | 學號，設定後 `login()` 可無參數呼叫 |
| `NTUT_PASSWORD` | nportal 密碼 |

亦可在 terminal 中直接 export：
```bash
export NTUT_STUDENT_ID=你的學號
export NTUT_PASSWORD=你的密碼
```

## Tools (18)

### get_school_calendar

取得北科大全校行事曆（Google Calendar iCal feed）。依日期範圍回傳活動：名稱、開始/結束時間、地點、說明。不須登入。

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `from_date` | string | 今天 | YYYY-MM-DD |
| `to_date` | string | from_date + 12 月 | YYYY-MM-DD |

不加參數時預設回傳今天起 12 個月內的事件。

### get_graduation_standard

取得課程標準（畢業科目表）。依參數決定回傳層級：

| 參數組合 | 回傳內容 |
|----------|----------|
| `year` only | 學制列表（四技、碩士班等） |
| `year` + `matric` | 系所列表（含各系學分統計） |
| `year` + `matric` + `division` | 完整課程科目表 + 畢業門檻 |

| 參數 | 類型 | 說明 |
|------|------|------|
| `year` | integer | 入學年度，例如 113 |
| `matric` | string | 學制代碼，例如 "7"（四技）。常用值：5=五專, 6=二技, 7=四技, 8=碩士班, 9=博士班, A=碩士在職班, F=進修部四技 |
| `division` | string | 系所代碼，例如 "590"（資工系）或 "823"（電資學士班資工） |

無須登入。

### login

登入 NTUT nportal 並執行 SSO 驗證（課程系統 + i 學園）。可傳入帳密，或設定環境變數 `NTUT_STUDENT_ID` / `NTUT_PASSWORD` 後無參數呼叫。登入成功時一併回傳姓名、email、角色。

| 參數 | 類型 | 說明 |
|------|------|------|
| `student_id` | string | 學號（可省略，改用環境變數） |
| `password` | string | nportal 密碼（可省略，改用環境變數） |

### logout

清除伺服器上的 session 並關閉連線。

無參數。

### get_semester_list

取得該學生所有修課學期代碼列表（例如 `["1132", "1131"]`）。

無參數。須先登入。

### get_timetable

取得指定學期的課表（二維陣列格式，第一列為星期標頭，第一欄為節次）。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼，例如 `"1142"`（114 年度第 2 學期） |

須先登入。

### get_course_list

取得指定學期的全部課程列表，包含 `course_id`（6 位數字）、課程名稱、學分數、狀態，並一併回傳總學分。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |

須先登入。回傳的 `course_id` 可用於其他 course tools。

### get_ischool_course_list

取得 i 學園上該學期所有課程（含退選）。回傳課程 ID、名稱、狀態（修課中 / 退選）。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |

須先登入。

### get_course_syllabus

取得指定課程的授課大綱：教師、學分、時數、必選修、修課人數、課程大綱、課程進度、評分標準、教科書、諮詢管道等。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字，從 `get_course_list` 取得） |

須先登入。

### get_course_description

取得指定課程的中文與英文簡介。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |

須先登入。

### ischool_file_download

從 i 學園下載課程檔案。`save_path` 為唯一必填參數，其餘依組合決定行為：

| `seme` | `course_id` | `index` | 行為 |
|:---:|:---:|:---:|------|
| 指定 | 指定 | ≥0 | 下載該檔案到 `save_path`（含檔名） |
| 指定 | 指定 | -1 | 下載該課程全部檔案到 `save_path/{課程名}_{課號}/` |
| 指定 | 空 | — | 下載該學期所有課程到 `save_path/{seme}/{課程名}_{課號}/` |
| 空 | — | — | 下載全部學期所有課程，按 `seme/課程/` 分層 |

支援自動重試（最多 3 次，指數退避），透過 `_downloads.json` 追蹤已下載檔案。

| 參數 | 類型 | 說明 |
|------|------|------|
| `save_path` | string | 本機儲存路徑或目錄 |
| `seme` | string | 學期代碼（可省略） |
| `course_id` | string | 課程代碼（6 位數字，可省略） |
| `index` | integer | 檔案索引（從 `get_course_asset_list` 取得，-1 = 不限） |

須先登入。

### get_course_asset_list

取得指定課程在 i 學園上的檔案與錄影列表。回傳每個項目的 `index`、標題、更新時間；檔案額外含檔名。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |

須先登入。

### get_course_video_url

取得指定影片的串流網址。成功時直接回傳 URL 字串，失敗回傳 `{"error": "..."}` 的 JSON 字串。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |
| `index` | integer | 影片索引（從 `get_course_asset_list` 取得） |

須先登入。

### get_bulletin_list

取得指定課程的公告列表（僅回傳索引、標題、時間、張貼者）。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |

須先登入。回傳的 `index` 用於 `get_bulletin`。

### get_bulletin

取得指定公告的完整內文與全部回覆。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |
| `index` | integer | 公告索引（從 `get_bulletin_list` 取得，0 = 第一則） |

須先登入。

### get_course_homework_list

取得指定課程在 i 學園上的作業/報告列表。回傳每個項目的 `index`、名稱、類型、狀態、截止日、完成度等。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |

須先登入。

### get_course_note

讀取指定課程的筆記（JSON 檔，含建立/更新時間戳）。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |
| `notes_dir` | string | 筆記儲存目錄路徑 |

### set_course_note

寫入指定課程的筆記（Markdown 格式）。自動建立目錄，保留首次建立時間。

| 參數 | 類型 | 說明 |
|------|------|------|
| `seme` | string | 學期代碼 |
| `course_id` | string | 課程代碼（6 位數字） |
| `content` | string | 筆記內容（支援 Markdown） |
| `notes_dir` | string | 筆記儲存目錄路徑 |

## 使用範例

在 AI 對話中直接說：

```
幫我查這學期的課表
查機率的大綱
機率有哪些錄影
查機率第 0 則公告的回覆
```

## 架構

```
├── main.py              # MCP 入口（FastMCP server）
├── server/
│   ├── __init__.py
│   └── tools/            # 18 個 MCP tool
│       ├── __init__.py       # FastMCP + session + 匯入
│       ├── _helpers.py       # _require_login, _ensure_course, _get_files_internal
│       ├── auth.py           # login (含 student info), logout
│       ├── semester.py       # get_semester_list
│       ├── timetable.py      # get_timetable, get_course_list (含 total_credits), get_ischool_course_list
│       ├── syllabus.py       # get_course_syllabus, get_course_description
│       ├── files.py          # ischool_file_download
│       ├── videos.py         # get_course_asset_list, get_course_video_url
│       ├── bulletin.py       # get_bulletin_list, get_bulletin
│       ├── homework.py       # get_course_homework_list
│       ├── calendar.py       # get_school_calendar (Google Calendar iCal)
│       ├── graduation.py     # get_graduation_standard (課程科目表)
│       └── notes.py          # get_course_note, set_course_note
├── nportal/
│   ├── __init__.py
│   ├── scraper.py       # httpx 網路爬蟲（session、login、SSO）
│   ├── session.py       # SessionManager（狀態管理、課表解析）
│   ├── course.py        # Course 類別（大綱、檔案、影片、公告）
│   ├── calendar.py      # 行事曆（iCal 抓取+解析）
│   ├── graduation.py    # 課程標準（Cprog.jsp 解析）
│   └── constants.py     # URL 常數
└── pyproject.toml
```

## License

MIT
