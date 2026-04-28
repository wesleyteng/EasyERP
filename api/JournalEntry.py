from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, col, select

from database import get_session
from models import JournalEntry, JournalEntryLine, JournalEntryType

router = APIRouter(tags=["Journal Entries"])


class JournalEntryLineCreate(BaseModel):
    line_no: int = 1
    account_code: str
    account_name: str
    summary: Optional[str] = None
    debit_amount: Decimal = Decimal("0.00")
    credit_amount: Decimal = Decimal("0.00")
    tax_code: Optional[str] = None
    project_code: Optional[str] = None
    reference_no: Optional[str] = None


class JournalEntryCreate(BaseModel):
    entry_no: str
    entry_date: datetime
    description: Optional[str] = None
    type: JournalEntryType = JournalEntryType.general
    currency: str = "TWD"
    exchange_rate: Decimal = Decimal("1.000000")
    note: Optional[str] = None
    lines: List[JournalEntryLineCreate]


class JournalEntryUpdate(BaseModel):
    entry_no: str
    entry_date: datetime
    description: Optional[str] = None
    type: JournalEntryType = JournalEntryType.general
    currency: str = "TWD"
    exchange_rate: Decimal = Decimal("1.000000")
    note: Optional[str] = None
    status: bool = True
    lines: List[JournalEntryLineCreate]


class JournalEntryLineRead(BaseModel):
    id: int
    line_no: int
    account_code: str
    account_name: str
    summary: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    tax_code: Optional[str] = None
    project_code: Optional[str] = None
    reference_no: Optional[str] = None

    class Config:
        from_attributes = True


class JournalEntryRead(BaseModel):
    id: UUID
    entry_no: str
    entry_date: datetime
    description: Optional[str] = None
    type: JournalEntryType
    currency: str
    exchange_rate: Decimal
    note: Optional[str] = None
    total_debit: Decimal
    total_credit: Decimal
    status: bool
    date_in: datetime
    update_time: datetime
    lines: List[JournalEntryLineRead] = []

    class Config:
        from_attributes = True


class JournalEntryListRead(BaseModel):
    id: UUID
    entry_no: str
    entry_date: datetime
    description: Optional[str] = None
    type: JournalEntryType
    currency: str
    exchange_rate: Decimal
    total_debit: Decimal
    total_credit: Decimal
    status: bool
    date_in: datetime

    class Config:
        from_attributes = True


def _validate_lines(lines: List[JournalEntryLineCreate]) -> tuple[Decimal, Decimal]:
    if len(lines) < 2:
        raise HTTPException(status_code=400, detail="傳票至少需要兩筆分錄明細")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for index, line in enumerate(lines, start=1):
        debit = line.debit_amount or Decimal("0.00")
        credit = line.credit_amount or Decimal("0.00")

        if debit < 0 or credit < 0:
            raise HTTPException(status_code=400, detail=f"第 {index} 筆明細金額不可為負數")
        if debit > 0 and credit > 0:
            raise HTTPException(status_code=400, detail=f"第 {index} 筆明細不可同時有借方與貸方")
        if debit == 0 and credit == 0:
            raise HTTPException(status_code=400, detail=f"第 {index} 筆明細借方與貸方不可同時為 0")

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise HTTPException(status_code=400, detail="借方合計必須等於貸方合計")

    return total_debit, total_credit


def _build_line(entry_id: UUID, line_in: JournalEntryLineCreate, index: int) -> JournalEntryLine:
    return JournalEntryLine(
        journal_entry_id=entry_id,
        line_no=line_in.line_no or index,
        account_code=line_in.account_code,
        account_name=line_in.account_name,
        summary=line_in.summary,
        debit_amount=line_in.debit_amount,
        credit_amount=line_in.credit_amount,
        tax_code=line_in.tax_code,
        project_code=line_in.project_code,
        reference_no=line_in.reference_no,
    )


@router.post("/", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
def create_journal_entry(entry_in: JournalEntryCreate, session: Session = Depends(get_session)):
    total_debit, total_credit = _validate_lines(entry_in.lines)

    existing_entry = session.exec(
        select(JournalEntry).where(JournalEntry.entry_no == entry_in.entry_no)
    ).first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="傳票號碼已存在")

    db_entry = JournalEntry(
        entry_no=entry_in.entry_no,
        entry_date=entry_in.entry_date,
        description=entry_in.description,
        type=entry_in.type,
        currency=entry_in.currency,
        exchange_rate=entry_in.exchange_rate,
        note=entry_in.note,
        total_debit=total_debit,
        total_credit=total_credit,
    )

    try:
        session.add(db_entry)
        session.flush()

        for index, line_in in enumerate(entry_in.lines, start=1):
            session.add(_build_line(db_entry.id, line_in, index))

        session.commit()
        session.refresh(db_entry)
        return db_entry
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"傳票建立失敗: {str(e)}")


@router.get("/", response_model=List[JournalEntryListRead])
def read_journal_entries(
    entry_no: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    type: Optional[JournalEntryType] = Query(None),
    currency: Optional[str] = Query(None),
    include_voided: bool = Query(False),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    statement = select(JournalEntry)

    if not include_voided:
        statement = statement.where(JournalEntry.status == True)
    if entry_no:
        statement = statement.where(col(JournalEntry.entry_no).contains(entry_no))
    if start_date:
        statement = statement.where(JournalEntry.entry_date >= start_date)
    if end_date:
        statement = statement.where(JournalEntry.entry_date <= end_date)
    if type:
        statement = statement.where(JournalEntry.type == type)
    if currency:
        statement = statement.where(JournalEntry.currency == currency)

    statement = statement.order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_no.desc())
    return session.exec(statement.offset(skip).limit(limit)).all()


@router.get("/{id}", response_model=JournalEntryRead)
def get_journal_entry(id: UUID, session: Session = Depends(get_session)):
    entry = session.get(JournalEntry, id)
    if not entry:
        raise HTTPException(status_code=404, detail="找不到傳票")
    return entry


@router.put("/{id}", response_model=JournalEntryRead)
def update_journal_entry(
    id: UUID,
    entry_in: JournalEntryUpdate,
    session: Session = Depends(get_session),
):
    db_entry = session.get(JournalEntry, id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="找不到傳票")

    duplicate_entry = session.exec(
        select(JournalEntry).where(
            JournalEntry.entry_no == entry_in.entry_no,
            JournalEntry.id != id,
        )
    ).first()
    if duplicate_entry:
        raise HTTPException(status_code=400, detail="傳票號碼已存在")

    total_debit, total_credit = _validate_lines(entry_in.lines)

    try:
        db_entry.entry_no = entry_in.entry_no
        db_entry.entry_date = entry_in.entry_date
        db_entry.description = entry_in.description
        db_entry.type = entry_in.type
        db_entry.currency = entry_in.currency
        db_entry.exchange_rate = entry_in.exchange_rate
        db_entry.note = entry_in.note
        db_entry.total_debit = total_debit
        db_entry.total_credit = total_credit
        db_entry.status = entry_in.status
        db_entry.update_time = datetime.now()

        old_lines = session.exec(
            select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == id)
        ).all()
        for old_line in old_lines:
            session.delete(old_line)

        for index, line_in in enumerate(entry_in.lines, start=1):
            session.add(_build_line(db_entry.id, line_in, index))

        session.add(db_entry)
        session.commit()
        session.refresh(db_entry)
        return db_entry
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"傳票更新失敗: {str(e)}")


@router.delete("/{id}")
def void_journal_entry(id: UUID, session: Session = Depends(get_session)):
    entry = session.get(JournalEntry, id)
    if not entry:
        raise HTTPException(status_code=404, detail="找不到傳票")

    entry.status = False
    entry.update_time = datetime.now()
    session.add(entry)
    session.commit()
    return {"ok": True, "message": "傳票已作廢"}
