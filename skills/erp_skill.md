### ERP 遠端操作技能
- **功能**: 開立報價單/收據
- **端點**: POST `/api/finance/invoice`
- **參數**: customer_name, items, total_amount
- **AI 邏輯**: 當老闆說「幫我開單」時，解析客戶名稱與品項，呼叫此 API，並將回傳的 PDF URL 發回 Line。