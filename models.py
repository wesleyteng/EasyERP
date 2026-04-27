from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum

# --- 1. 定義列舉型別 (Enums) ---
class PartnerType(str, Enum):
    customer = "customer" # 客戶 (AR對象)
    supplier = "supplier" # 供應商 (AP對象)

class InvoiceType(str, Enum):
    ar = "AR" # 應收帳款 (Account Receivable)
    ap = "AP" # 應付帳款 (Account Payable)

class TransactionType(str, Enum):
    inbound = "in"   # 進貨/入庫
    outbound = "out" # 出貨/出庫

# --- 2. 定義資料表模型 ---

# 合作夥伴 (客戶/供應商)
class Partner(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: PartnerType
    contact_info: Optional[str] = None

    # 關聯：一個夥伴可以有多張單據
    invoices: List["Invoice"] = Relationship(back_populates="partner")

# 庫存品項
class InventoryItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True) # 產品編號
    name: str
    current_stock: int = Field(default=0)     # 目前庫存量
    unit_price: float = Field(default=0.0)    # 單價

    # 關聯：一個品項可以有多筆進出貨異動
    transactions: List["Transaction"] = Relationship(back_populates="item")

# 財務單據 (應收/應付)
class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    partner_id: int = Field(foreign_key="partner.id")
    type: InvoiceType
    total_amount: float
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    is_paid: bool = Field(default=False) # 是否已沖銷/結清

    # 關聯
    partner: Optional[Partner] = Relationship(back_populates="invoices")
    transactions: List["Transaction"] = Relationship(back_populates="invoice")

# 庫存異動明細 (進出貨紀錄)
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="inventoryitem.id")
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    type: TransactionType
    quantity: int # 異動數量
    transaction_date: datetime = Field(default_factory=datetime.utcnow)

    # 關聯
    item: Optional[InventoryItem] = Relationship(back_populates="transactions")
    invoice: Optional[Invoice] = Relationship(back_populates="transactions")