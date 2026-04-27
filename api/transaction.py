from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from models import Invoice, Partner, InventoryItem, Transaction, TransactionType

router = APIRouter()

# 1. 開立帳單 (POST /invoices/)
@router.post("/invoices/", response_model=Invoice)
def create_invoice(invoice: Invoice, session: Session = Depends(get_session)):
    partner = session.get(Partner, invoice.partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="找不到指定的合作夥伴")
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice

# 2. 查詢帳單 (GET /invoices/)
@router.get("/invoices/", response_model=List[Invoice])
def read_invoices(session: Session = Depends(get_session)):
    invoices = session.exec(select(Invoice)).all()
    return invoices

# 3. 新增進出貨紀錄 (POST /transactions/) - 核心庫存連動邏輯
@router.post("/transactions/", response_model=Transaction)
def create_transaction(transaction: Transaction, session: Session = Depends(get_session)):
    # 取得對應的庫存品項
    item = session.get(InventoryItem, transaction.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到指定的庫存品項")

    # 根據進出貨類型更新庫存
    if transaction.type == TransactionType.inbound:
        item.current_stock += transaction.quantity
    elif transaction.type == TransactionType.outbound:
        # 出貨時檢查庫存是否足夠
        if item.current_stock < transaction.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"庫存不足！目前 {item.name} 僅剩 {item.current_stock} 件。"
            )
        item.current_stock -= transaction.quantity

    # 將 Transaction 與更新後的 Item 加入同一個 Session，確保資料庫的一致性
    session.add(transaction)
    session.add(item)
    session.commit()
    session.refresh(transaction)
    return transaction

# 4. 查詢進出貨紀錄 (GET /transactions/)
@router.get("/transactions/", response_model=List[Transaction])
def read_transactions(session: Session = Depends(get_session)):
    transactions = session.exec(select(Transaction)).all()
    return transactions