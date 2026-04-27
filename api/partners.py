from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, col
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from database import get_session
from models import Partner

router = APIRouter(tags=["Partners (客戶與供應商)"])

# --- Pydantic Schemas ---

class PartnerCreate(BaseModel):
    type: int = 0
    name: Optional[str] = None
    serial_no: Optional[str] = None
    erp_id: str
    contact: Optional[str] = None
    contact_tel: Optional[str] = None
    tel: Optional[str] = None
    fax: Optional[str] = None
    zip: Optional[str] = None
    address: Optional[str] = None
    boss: Optional[str] = None
    invoice_address: Optional[str] = None
    invoice_zip: Optional[str] = None
    payment_tel: Optional[str] = None
    status: bool = True

class PartnerUpdate(BaseModel):
    type: Optional[int] = None
    name: Optional[str] = None
    serial_no: Optional[str] = None
    erp_id: Optional[str] = None
    contact: Optional[str] = None
    contact_tel: Optional[str] = None
    tel: Optional[str] = None
    fax: Optional[str] = None
    zip: Optional[str] = None
    address: Optional[str] = None
    boss: Optional[str] = None
    invoice_address: Optional[str] = None
    invoice_zip: Optional[str] = None
    payment_tel: Optional[str] = None
    status: Optional[bool] = None

# --- API 路由實作 ---

@router.post("/", response_model=Partner, status_code=status.HTTP_201_CREATED)
def create_partner(partner_in: PartnerCreate, session: Session = Depends(get_session)):
    """
    建立新的合作夥伴。
    """
    db_partner = Partner.from_orm(partner_in)
    session.add(db_partner)
    session.commit()
    session.refresh(db_partner)
    return db_partner

@router.get("/", response_model=List[Partner])
def search_partners(
    type: Optional[int] = Query(None, description="過濾廠商類型 (0:一般, 1:客戶, 2:供應商等)"),
    name: Optional[str] = Query(None, description="依據名稱進行模糊搜尋"),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    查詢所有合作夥伴，支援依據類型過濾與名稱模糊搜尋。
    """
    statement = select(Partner)
    
    if type is not None:
        statement = statement.where(Partner.type == type)
    
    if name:
        # 使用 col().contains 進行模糊搜尋 (LIKE %name%)
        statement = statement.where(col(Partner.name).contains(name))
    
    partners = session.exec(statement.offset(skip).limit(limit)).all()
    return partners

@router.get("/{id}", response_model=Partner)
def read_partner(id: UUID, session: Session = Depends(get_session)):
    """
    取得特定合作夥伴細節。
    """
    partner = session.get(Partner, id)
    if not partner:
        raise HTTPException(status_code=404, detail="找不到該合作夥伴")
    return partner

@router.patch("/{id}", response_model=Partner)
def update_partner(id: UUID, partner_in: PartnerUpdate, session: Session = Depends(get_session)):
    """
    更新合作夥伴資訊。
    """
    db_partner = session.get(Partner, id)
    if not db_partner:
        raise HTTPException(status_code=404, detail="找不到該合作夥伴")
    
    partner_data = partner_in.dict(exclude_unset=True)
    for key, value in partner_data.items():
        setattr(db_partner, key, value)
    
    session.add(db_partner)
    session.commit()
    session.refresh(db_partner)
    return db_partner

@router.delete("/{id}")
def delete_partner(id: UUID, session: Session = Depends(get_session)):
    """
    刪除合作夥伴。
    """
    partner = session.get(Partner, id)
    if not partner:
        raise HTTPException(status_code=404, detail="找不到該合作夥伴")
    session.delete(partner)
    session.commit()
    return {"ok": True}
