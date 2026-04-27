from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from database import get_session
from models import POrder, POrderProduct, Partner

router = APIRouter(tags=["Orders"])

# --- Pydantic 接收模型 (Schemas) ---

class POrderProductCreate(BaseModel):
    product_id: int
    description: Optional[str] = None
    amount: Decimal = Decimal(0)
    spec: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    note: Optional[str] = None

class POrderCreate(BaseModel):
    project_id: Optional[UUID] = None
    user_id: UUID
    vendor_id: UUID
    erp_id: Optional[str] = None
    order_no: str
    type: int = 0
    comp: int = 0
    total_price: int = 0
    contact: Optional[str] = None
    contact_tel: Optional[str] = None
    ship_address: Optional[str] = None
    ship_note: Optional[str] = None
    ship_date: Optional[datetime] = None
    products: List[POrderProductCreate]

# --- Pydantic 回傳模型 (Response Schemas) ---

class PartnerRead(BaseModel):
    id: UUID
    name: Optional[str] = None
    erp_id: str
    contact: Optional[str] = None

    class Config:
        from_attributes = True

class POrderProductRead(BaseModel):
    id: int
    product_id: int
    description: Optional[str] = None
    amount: Decimal
    spec: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True

class POrderRead(BaseModel):
    id: UUID
    order_no: str
    user_id: UUID
    vendor_id: UUID
    vendor: Optional[PartnerRead] = None
    products: List[POrderProductRead] = []
    total_price: int
    date_in: datetime
    status: bool
    project_id: Optional[UUID] = None
    erp_id: Optional[str] = None
    type: int
    comp: int
    contact: Optional[str] = None
    contact_tel: Optional[str] = None
    ship_address: Optional[str] = None
    ship_note: Optional[str] = None
    ship_date: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- API 路由實作 ---

@router.get("/", response_model=List[POrderRead])
def read_orders(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """
    查詢所有訂單列表。
    """
    return session.exec(select(POrder).offset(skip).limit(limit)).all()

@router.post("/", response_model=POrderRead, status_code=status.HTTP_201_CREATED)
def create_order(order_in: POrderCreate, session: Session = Depends(get_session)):
    """
    建立訂單 (POST /orders): 同時寫入主檔與多筆明細，並確保交易一致性。
    """
    # 1. 建立 POrder 主檔物件
    db_order = POrder(
        project_id=order_in.project_id,
        user_id=order_in.user_id,
        vendor_id=order_in.vendor_id,
        erp_id=order_in.erp_id,
        order_no=order_in.order_no,
        type=order_in.type,
        comp=order_in.comp,
        total_price=order_in.total_price,
        contact=order_in.contact,
        contact_tel=order_in.contact_tel,
        ship_address=order_in.ship_address,
        ship_note=order_in.ship_note,
        ship_date=order_in.ship_date
    )
    
    try:
        # 開始交易 (SQLModel Session 預設在 commit 前都是同一個 Transaction)
        session.add(db_order)
        session.flush()  # 取得 db_order.id (UUID) 以供明細使用
        
        # 2. 建立 POrderProduct 明細物件
        for p_in in order_in.products:
            db_item = POrderProduct(
                order_id=db_order.id,
                product_id=p_in.product_id,
                description=p_in.description,
                amount=p_in.amount,
                spec=p_in.spec,
                unit=p_in.unit,
                unit_price=p_in.unit_price,
                total_price=p_in.total_price,
                note=p_in.note
            )
            session.add(db_item)
            
        # 3. 提交交易
        session.commit()
        session.refresh(db_order)
        return db_order
        
    except Exception as e:
        # 發生錯誤時 Rollback
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"訂單建立失敗: {str(e)}"
        )

@router.get("/{id}", response_model=POrderRead)
def get_order(id: UUID, session: Session = Depends(get_session)):
    """
    查詢訂單 (GET /orders/{id}): 回傳訂單時包含 vendor 資訊與 products 明細。
    """
    order = session.get(POrder, id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="找不到該訂單"
        )
    return order
