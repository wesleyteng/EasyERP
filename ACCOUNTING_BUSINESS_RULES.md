# Accounting Business Rules

## Journal Entry
- 一張傳票包含表頭與多筆分錄明細
- 借方合計必須等於貸方合計才能儲存
- 每筆分錄不可同時有借方與貸方
- 金額不可為負數
- 傳票號碼不可重複

## Posting
- 只有 draft 傳票可以過帳
- posted 傳票不可修改
- posted 傳票不可硬刪除
- 更正錯誤需使用反向傳票或調整傳票
- 總帳與 Trial Balance 只統計 posted 傳票

## Reports
- General Ledger 必須支援日期區間與科目篩選
- Trial Balance 必須驗證借貸合計相等