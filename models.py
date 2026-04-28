from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from decimal import Decimal
import uuid
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


# --- 2. 原有基礎資料表模型 ---

# 合作夥伴 (客戶/供應商)
class Partner(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True, nullable=False)
    type: int = Field(default=0, description="廠商類型")
    name: Optional[str] = Field(default=None, max_length=200)
    serial_no: Optional[str] = Field(default=None, max_length=8)
    erp_id: str = Field(max_length=50, nullable=False)
    contact: Optional[str] = Field(default=None, max_length=50)
    contact_tel: Optional[str] = Field(default=None, max_length=50)
    tel: Optional[str] = Field(default=None, max_length=50)
    fax: Optional[str] = Field(default=None, max_length=50)
    zip: Optional[str] = Field(default=None, max_length=10)
    address: Optional[str] = Field(default=None, max_length=500)
    boss: Optional[str] = Field(default=None, max_length=50)
    invoice_address: Optional[str] = Field(default=None, max_length=300)
    invoice_zip: Optional[str] = Field(default=None, max_length=10)
    payment_tel: Optional[str] = Field(default=None, max_length=50)
    status: bool = Field(default=True)
    date_in: datetime = Field(default_factory=datetime.now)

    invoices: List["Invoice"] = Relationship(back_populates="partner")
    orders: List["POrder"] = Relationship(back_populates="vendor")

# 財務單據 (應收/應付)
class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    partner_id: uuid.UUID = Field(foreign_key="partner.id")
    type: InvoiceType
    total_amount: float
    invoice_date: datetime = Field(default_factory=datetime.now)
    is_paid: bool = Field(default=False)

    partner: Optional[Partner] = Relationship(back_populates="invoices")
    transactions: List["Transaction"] = Relationship(back_populates="invoice")

# 庫存品項
class InventoryItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name: str
    current_stock: int = Field(default=0)
    unit_price: float = Field(default=0.0)

    transactions: List["Transaction"] = Relationship(back_populates="item")

# 庫存異動明細
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="inventoryitem.id")
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    type: TransactionType
    quantity: int
    transaction_date: datetime = Field(default_factory=datetime.now)

    item: Optional[InventoryItem] = Relationship(back_populates="transactions")
    invoice: Optional[Invoice] = Relationship(back_populates="transactions")

# 商品主檔
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_no: Optional[str] = Field(default=None, max_length=50)
    erp_id: Optional[str] = Field(default=None, max_length=50)
    catalog: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=50)
    short_name: Optional[str] = Field(default=None, max_length=50)
    unit: Optional[str] = Field(default=None, max_length=50)
    show_price: Decimal = Field(default=0, max_digits=18, decimal_places=2)
    sales_price: Decimal = Field(default=0, max_digits=18, decimal_places=2)
    bottom_price: Decimal = Field(default=0, max_digits=18, decimal_places=2)
    cost: Decimal = Field(default=0, max_digits=18, decimal_places=2)
    is_green: bool = Field(default=True)
    on_shelf: bool = Field(default=True)
    status: bool = Field(default=True)
    date_in: Optional[datetime] = Field(default_factory=datetime.now)


# --- 3. 新增訂單模組資料表模型 ---

# 訂單流水號設定檔
class POrderNumber(SQLModel, table=True):
    pre_position: str = Field(primary_key=True, max_length=15)
    count: int = Field(description="目前流水號計數")

# 訂單主檔
class POrder(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: Optional[uuid.UUID] = Field(default=None)
    user_id: uuid.UUID = Field(nullable=False)
    vendor_id: uuid.UUID = Field(foreign_key="partner.id", nullable=False)
    erp_id: Optional[str] = Field(default=None, max_length=50)
    order_no: str = Field(max_length=20, nullable=False)
    type: int = Field(default=0)
    comp: int = Field(default=0)
    total_price: int = Field(default=0)
    contact: Optional[str] = Field(default=None, max_length=50)
    contact_tel: Optional[str] = Field(default=None, max_length=50)
    ship_address: Optional[str] = Field(default=None, max_length=300)
    ship_note: Optional[str] = Field(default=None, max_length=500)
    date_in: datetime = Field(default_factory=datetime.now)
    update_time: datetime = Field(default_factory=datetime.now)
    status: bool = Field(default=True)
    ship_date: Optional[datetime] = Field(default=None)

    vendor: Optional[Partner] = Relationship(back_populates="orders")
    products: List["POrderProduct"] = Relationship(back_populates="order", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    status_history: List["POrderStatus"] = Relationship(back_populates="order", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

# 訂單明細
class POrderProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="porder.id", nullable=False)
    product_id: int = Field(foreign_key="product.id", nullable=False)
    description: Optional[str] = Field(default=None, max_length=300)
    amount: Decimal = Field(default=0, max_digits=18, decimal_places=2)
    spec: Optional[str] = Field(default=None, max_length=200)
    unit: Optional[str] = Field(default=None, max_length=50)
    unit_price: Optional[Decimal] = Field(default=None, max_digits=18, decimal_places=2)
    total_price: Optional[Decimal] = Field(default=None, max_digits=18, decimal_places=2)
    note: Optional[str] = Field(default=None, max_length=1000)

    order: Optional[POrder] = Relationship(back_populates="products")
    product: Optional[Product] = Relationship()

# 訂單狀態歷程
class POrderStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="porder.id", nullable=False)
    user_id: uuid.UUID = Field(nullable=False)
    status: int = Field(nullable=False)
    date_in: datetime = Field(default_factory=datetime.now)

    # 之前遺漏的關鍵關聯！
    order: Optional[POrder] = Relationship(back_populates="status_history")


# --- 4. 權限管理模組資料表模型 ---

# 後台帳號
class BackendAccount(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True, nullable=False)
    username: str = Field(max_length=100, index=True, nullable=False)
    password: str = Field(max_length=100, nullable=False)
    name: str = Field(max_length=50, nullable=False)
    role_id_list: Optional[str] = Field(default=None, max_length=100)
    status: bool = Field(default=True)
    date_in: datetime = Field(default_factory=datetime.now)


# --- 5. Journal Entry Models ---

class JournalEntryType(str, Enum):
    general = "general"
    adjustment = "adjustment"
    closing = "closing"
    reversing = "reversing"


class JournalEntry(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True, nullable=False)
    entry_no: str = Field(max_length=30, nullable=False, index=True, unique=True)
    entry_date: datetime = Field(nullable=False)
    description: Optional[str] = Field(default=None, max_length=300)
    type: JournalEntryType = Field(default=JournalEntryType.general, nullable=False)
    currency: str = Field(default="TWD", max_length=10, nullable=False)
    exchange_rate: Decimal = Field(default=Decimal("1.000000"), max_digits=18, decimal_places=6)
    note: Optional[str] = Field(default=None, max_length=1000)
    total_debit: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    total_credit: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    status: bool = Field(default=True)
    date_in: datetime = Field(default_factory=datetime.now)
    update_time: datetime = Field(default_factory=datetime.now)

    lines: List["JournalEntryLine"] = Relationship(
        back_populates="entry",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class JournalEntryLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    journal_entry_id: uuid.UUID = Field(foreign_key="journalentry.id", nullable=False)
    line_no: int = Field(default=1)
    account_code: str = Field(max_length=50, nullable=False)
    account_name: str = Field(max_length=200, nullable=False)
    summary: Optional[str] = Field(default=None, max_length=300)
    debit_amount: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    credit_amount: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    tax_code: Optional[str] = Field(default=None, max_length=30)
    project_code: Optional[str] = Field(default=None, max_length=50)
    reference_no: Optional[str] = Field(default=None, max_length=100)

    entry: Optional[JournalEntry] = Relationship(back_populates="lines")
