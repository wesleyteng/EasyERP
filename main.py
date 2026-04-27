from fastapi import FastAPI
from sqlmodel import SQLModel
from database import engine
import models # <--- 關鍵修改：必須引入 models，引擎才知道要建哪些表！
from fastapi.staticfiles import StaticFiles

# 暫時先註解掉這兩行，因為裡面的檔案還是空的
from api import ap_ar, inventory, transaction

app = FastAPI(title="EasyERP (微型企業自動化ERP)", version="0.1.0")
app.mount("/ui", StaticFiles(directory="frontend"), name="ui")

# 啟動時自動建立資料表
@app.on_event("startup")
def on_startup():
    print("正在建立資料表...")
    SQLModel.metadata.create_all(engine)
    print("資料表檢查/建立完成！")

# 暫時註解掉路由，等下一步我們寫好 API 再打開
app.include_router(ap_ar.router, prefix="/api/finance", tags=["Finance (財務與對象)"])
app.include_router(inventory.router, prefix="/api/warehouse", tags=["Warehouse (庫存管理)"])
app.include_router(transaction.router, prefix="/api/operation", tags=["Operation (進出貨與單據)"])

@app.get("/")
def read_root():
    return {"message": "歡迎來到 EasyERP 系統後端 API"}