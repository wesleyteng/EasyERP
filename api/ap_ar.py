from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Partner

router = APIRouter()

# 1. 新增合作夥伴 (客戶/供應商)
@router.post("/partners/", response_model=Partner)
def create_partner(partner: Partner, session: Session = Depends(get_session)):
    session.add(partner)
    session.commit()
    session.refresh(partner)
    return partner

# 2. 查詢所有合作夥伴
@router.get("/partners/", response_model=list[Partner])
def read_partners(session: Session = Depends(get_session)):
    partners = session.exec(select(Partner)).all()
    return partners