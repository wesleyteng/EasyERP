from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, col
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
def read_orders(
    order_no: Optional[str] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    """
    查詢訂單列表，支援多種篩選條件。
    """
    statement = select(POrder)
    if order_no:
        statement = statement.where(col(POrder.order_no).contains(order_no))
    if vendor_id:
        statement = statement.where(POrder.vendor_id == vendor_id)
    if start_date:
        statement = statement.where(POrder.date_in >= start_date)
    if end_date:
        statement = statement.where(POrder.date_in <= end_date)
    
    # 按日期降冪排序 (最新的在前)
    statement = statement.order_by(POrder.date_in.desc())
    
    return session.exec(statement.offset(skip).limit(limit)).all()

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

from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
import pdfkit
import urllib.parse
import io
import os

templates = Jinja2Templates(directory="templates")

@router.get("/{id}/pdf")
def export_order_pdf(id: UUID, session: Session = Depends(get_session)):
    """
    匯出訂單為 PDF 出貨單格式。
    """
    # 1. 撈取訂單與關聯資料
    order = session.get(POrder, id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")

    # 2. 準備渲染資料 (Jinja2)
    # templates.get_template 也可以，但這裡我們手動渲染以取得 HTML 字串
    template_path = os.path.join("templates", "invoice.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    from jinja2 import Template
    jinja_template = Template(template_content)
    html_content = jinja_template.render(order=order)

    # 3. 轉換為 PDF
    # options 確保中文能正確顯示 (需系統有對應字體)
    options = {
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'quiet': '',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
    }
    
    # 如果是 Windows 且 wkhtmltopdf 不在 PATH 中，需指定路徑 (此處假設已在 PATH 中或為 Linux 環境)
    # config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    # pdf_data = pdfkit.from_string(html_content, False, options=options, configuration=config)
    
    try:
        pdf_data = pdfkit.from_string(html_content, False, options=options)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 轉換失敗: {str(e)}。請確認伺服器已安裝 wkhtmltopdf。")

    # 4. 處理檔名與回傳
    vendor_name = order.vendor.name if order.vendor else "客戶"
    filename = f"{order.order_no}_{vendor_name}.pdf"
    
    # URL 編碼檔名以支援中文
    encoded_filename = urllib.parse.quote(filename)
    
    return StreamingResponse(
        io.BytesIO(pdf_data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
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

@router.put("/{id}", response_model=POrderRead)
def update_order(id: UUID, order_in: POrderCreate, session: Session = Depends(get_session)):
    """
    更新訂單 (PUT /orders/{id}): 更新主檔並替換所有明細。
    """
    db_order = session.get(POrder, id)
    if not db_order:
        raise HTTPException(status_code=404, detail="找不到該訂單")

    # 1. 更新主檔欄位
    update_data = order_in.dict(exclude={"products"})
    for key, value in update_data.items():
        setattr(db_order, key, value)
    
    try:
        # 2. 刪除舊明細
        old_products = session.exec(select(POrderProduct).where(POrderProduct.order_id == id)).all()
        for old_p in old_products:
            session.delete(old_p)
        
        # 3. 建立新明細
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
            
        session.commit()
        session.refresh(db_order)
        return db_order
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"更新失敗: {str(e)}")
