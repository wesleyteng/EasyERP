# DOMAIN_RULES.md

## Core Principles

### 1. 所有交易都應可追溯
- 訂單 → 庫存 → 會計 必須能追蹤來源

### 2. 不可直接修改歷史交易
- 訂單、傳票、庫存異動不可直接改
- 必須透過補單 / 反向單

### 3. 狀態機（State Machine）
- Draft → Confirmed → Posted → Void
- 所有模組需一致

### 4. 金額與數量分離
- Quantity ≠ Amount
- 不可混用

### 5. 資料不可重算（避免帳亂）
- 一旦過帳，不可重新計算歷史數據

### 6. ERP 模組關聯
- Order → Inventory Movement → Journal Entry