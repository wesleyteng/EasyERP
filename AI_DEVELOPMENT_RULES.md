# AI Development Rules

## General
- 修改前先閱讀本檔與 ACCOUNTING_BUSINESS_RULES.md
- 不可一次大範圍改動，需分階段修改
- 修改前先說明會改哪些檔案
- 不可刪除既有功能
- 不可使用破壞性資料庫操作
- 完成後需檢查 import、route 註冊、啟動錯誤

## Backend Architecture
- 每個模組：
  - models/
  - api/
  - service/
- 不要把邏輯寫在 route

## Stack
- Backend: FastAPI + SQLModel
- Frontend: HTML + Tailwind CSS
- 金額欄位不可使用 float