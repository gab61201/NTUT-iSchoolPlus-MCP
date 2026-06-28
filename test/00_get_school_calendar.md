# get_school_calendar

不須登入。

## 參數

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `from_date` | string | 今天 | YYYY-MM-DD |
| `to_date` | string | from_date + 12 月 | YYYY-MM-DD |

不加參數 → 今天起 12 個月內。資料來源從 2019 年到 2027 年共 660 筆，過濾後約 100 筆。

## 不加參數（default）

```json
{
  "events": [
    {"index": 150, "summary": "暑期服務隊開始", "start": "2027-06-28 00:00:00", "end": "2027-06-29 00:00:00"},
    ...
  ]
}
```

97 events (from 660 total), range 2026-06-29 ~ 2027-06-29

## 指定範圍

```json
// from_date=2026-02-01, to_date=2026-02-28
{"events": [
  {"index": 121, "summary": "和平紀念日", "start": "2026-02-28 00:00:00", "end": "2026-03-01 00:00:00"},
  {"index": 116, "summary": "開學日開始上課、註冊截止日", "start": "2026-02-23 00:00:00", "end": "2026-02-24 00:00:00"},
  {"index": 114, "summary": "學期住宿開放", "start": "2026-02-21 00:00:00", "end": "2026-02-22 00:00:00"},
  ...
]}
```

12 events for 2026-Feb.

## 統計（原始資料 660 筆）

| 項目 | 值 |
|------|-----|
| 總事件數 | 660 |
| 日期範圍 | 2019-05-27 ~ 2027-07-04 |
| 含地點 | 7 筆 |
| 含描述 | 51 筆 |
| 全日活動 | 584 筆 |
| 含時間 | 76 筆 |

### 注意

- Summary 為 UTF-8 中文，PowerShell 終端可能顯示亂碼，但資料本身正確
- 部分早期事件（2019）有 HTML 格式的 description
- iCal URL：`calendar.google.com/calendar/ical/docfuhim9b22fqvp2tk842ak3c%40group.calendar.google.com/public/basic.ics`
