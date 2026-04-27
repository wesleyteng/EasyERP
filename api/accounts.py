from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from database import get_session
from models import BackendAccount

router = APIRouter(tags=["Accounts (帳號權限管理)"])

# --- Pydantic Schemas ---

class AccountCreate(BaseModel):
    username: str
    password: str
    name: str
    role_id_list: Optional[str] = "22" # 預設一般用戶

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    role_id_list: Optional[str] = None
    status: Optional[bool] = None

class AccountRead(BaseModel):
    id: UUID
    username: str
    name: str
    role_id_list: Optional[str] = None
    status: bool
    date_in: datetime

    class Config:
        from_attributes = True

class PasswordReset(BaseModel):
    new_password: str

# --- API 路由實作 ---

@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(account_in: AccountCreate, session: Session = Depends(get_session)):
    try:
        existing_user = session.exec(select(BackendAccount).where(BackendAccount.username == account_in.username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="此帳號名稱已存在")
        
        db_account = BackendAccount(**account_in.dict())
        session.add(db_account)
        session.commit()
        session.refresh(db_account)
        return db_account
    except HTTPException: raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"伺服器內部錯誤: {str(e)}")

@router.get("/", response_model=List[AccountRead])
def read_accounts(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return session.exec(select(BackendAccount).offset(skip).limit(limit)).all()

@router.patch("/{id}", response_model=AccountRead)
def update_account(id: UUID, account_in: AccountUpdate, session: Session = Depends(get_session)):
    db_account = session.get(BackendAccount, id)
    if not db_account:
        raise HTTPException(status_code=404, detail="找不到該帳號")
    
    account_data = account_in.dict(exclude_unset=True)
    for key, value in account_data.items():
        setattr(db_account, key, value)
    
    session.add(db_account)
    session.commit()
    session.refresh(db_account)
    return db_account

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(BackendAccount).where(BackendAccount.username == data.username)).first()
    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    if not user.status:
        raise HTTPException(status_code=403, detail="此帳號已被停用")
    
    return {
        "id": str(user.id),
        "username": user.username,
        "name": user.name,
        "role_id_list": user.role_id_list
    }

@router.patch("/reset-password/{id}")
def reset_password(id: UUID, data: PasswordReset, session: Session = Depends(get_session)):
    db_account = session.get(BackendAccount, id)
    if not db_account:
        raise HTTPException(status_code=404, detail="找不到該帳號")
    db_account.password = data.new_password
    session.add(db_account)
    session.commit()
    return {"message": "密碼重設成功"}

@router.delete("/{id}")
def delete_account(id: UUID, session: Session = Depends(get_session)):
    account = session.get(BackendAccount, id)
    if not account:
        raise HTTPException(status_code=404, detail="找不到該帳號")
    session.delete(account)
    session.commit()
    return {"ok": True}
