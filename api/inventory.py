from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import InventoryItem

# 建立 Router，這個會被 main.py 引入
router = APIRouter()

# 1. 新增商品
@router.post("/items/", response_model=InventoryItem)
def create_item(item: InventoryItem, session: Session = Depends(get_session)):
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

# 2. 查詢所有商品
@router.get("/items/", response_model=list[InventoryItem])
def read_items(session: Session = Depends(get_session)):
    items = session.exec(select(InventoryItem)).all()
    return items