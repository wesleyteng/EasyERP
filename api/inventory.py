from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_session
from models import Product, InventoryItem, Transaction, TransactionType

router = APIRouter(tags=["Inventory & Products"])

# --- Pydantic Schemas ---

# Product Schemas
class ProductCreate(BaseModel):
    product_no: Optional[str] = None
    erp_id: Optional[str] = None
    catalog: Optional[int] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    unit: Optional[str] = None
    show_price: float = 0.0
    sales_price: float = 0.0
    bottom_price: float = 0.0
    cost: float = 0.0
    is_green: bool = True
    on_shelf: bool = True

class ProductUpdate(BaseModel):
    product_no: Optional[str] = None
    erp_id: Optional[str] = None
    catalog: Optional[int] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    unit: Optional[str] = None
    show_price: Optional[float] = None
    sales_price: Optional[float] = None
    bottom_price: Optional[float] = None
    cost: Optional[float] = None
    is_green: Optional[bool] = None
    on_shelf: Optional[bool] = None
    status: Optional[bool] = None

# Transaction Schema
class InventoryTransactionCreate(BaseModel):
    item_id: int
    type: TransactionType
    quantity: int
    invoice_id: Optional[int] = None

@router.get("/", response_model=List[InventoryItem])
def read_inventory_items(session: Session = Depends(get_session)):
    """
    取得所有庫存品項狀態。
    """
    return session.exec(select(InventoryItem)).all()

# --- 1. 商品主檔 (Product) CRUD ---

@router.post("/products/", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, session: Session = Depends(get_session)):
    """
    建立商品主檔，並同步在 InventoryItem 建立初始庫存紀錄。
    """
    # 1. 建立商品主檔
    db_product = Product.from_orm(product_in)
    session.add(db_product)
    session.flush() # 取得 db_product.id
    
    # 2. 同步建立庫存品項 (InventoryItem)
    # 使用商品編號作為 SKU，商品名稱作為名稱
    new_inventory_item = InventoryItem(
        sku=db_product.product_no or f"PROD-{db_product.id}",
        name=db_product.name or "未命名商品",
        current_stock=0,
        unit_price=float(db_product.cost)
    )
    session.add(new_inventory_item)
    
    session.commit()
    session.refresh(db_product)
    return db_product

@router.get("/products/", response_model=List[Product])
def read_products(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    products = session.exec(select(Product).offset(skip).limit(limit)).all()
    return products

@router.get("/products/{product_id}", response_model=Product)
def read_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")
    return product

@router.patch("/products/{product_id}", response_model=Product)
def update_product(product_id: int, product_in: ProductUpdate, session: Session = Depends(get_session)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="找不到該商品")
    
    product_data = product_in.dict(exclude_unset=True)
    for key, value in product_data.items():
        setattr(db_product, key, value)
    
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
def delete_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")
    session.delete(product)
    session.commit()
    return {"ok": True}

# --- 2. 庫存異動邏輯 (Transaction) ---

@router.post("/transaction", status_code=status.HTTP_201_CREATED)
def create_inventory_transaction(tx_in: InventoryTransactionCreate, session: Session = Depends(get_session)):
    """
    庫存異動端點：
    1. 新增 Transaction 紀錄。
    2. 自動加減 InventoryItem 的 current_stock。
    3. 防呆：出貨時檢查庫存是否充足。
    """
    # 1. 取得 InventoryItem
    item = session.get(InventoryItem, tx_in.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到庫存品項")

    # 2. 判斷異動類型並檢查庫存
    if tx_in.type == TransactionType.outbound:
        if item.current_stock < tx_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"庫存不足。目前庫存: {item.current_stock}, 請求數量: {tx_in.quantity}"
            )
        # 出貨：減少庫存
        item.current_stock -= tx_in.quantity
    elif tx_in.type == TransactionType.inbound:
        # 進貨：增加庫存
        item.current_stock += tx_in.quantity
    else:
        raise HTTPException(status_code=400, detail="無效的異動類型")

    try:
        # 3. 建立 Transaction 紀錄
        db_tx = Transaction(
            item_id=tx_in.item_id,
            invoice_id=tx_in.invoice_id,
            type=tx_in.type,
            quantity=tx_in.quantity,
            transaction_date=datetime.now()
        )
        
        session.add(db_tx)
        session.add(item)  # 更新 InventoryItem 數量
        session.commit()
        session.refresh(db_tx)
        session.refresh(item)
        
        return {
            "message": "庫存異動成功",
            "transaction_id": db_tx.id,
            "new_stock": item.current_stock
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")
