import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

# 載入 .env 檔案中的環境變數
load_dotenv()

# 從環境變數讀取剛才設定的 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 確保 URL 是針對 async 或特定 driver 調整 (如果 psycopg2 遇到問題，有時會用 postgresql+psycopg2://)
# 但標準的 postgresql:// 通常可以直接由 SQLAlchemy/SQLModel 識別
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 建立資料庫引擎 (echo=True 可以在終端機看到 AI 生成的 SQL 語法，對初期除錯非常有幫助)
engine = create_engine(DATABASE_URL, echo=True)

# 建立 Session 產生器，未來 FastAPI 的 API 端點會透過這個函數來存取資料庫
def get_session():
    with Session(engine) as session:
        yield session