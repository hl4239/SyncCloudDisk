import logging
from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel, create_engine
from models.resource import Resource # 确保从正确的路径导入 Resource 模型

# 定义 SQLite 数据库文件路径
# 您可以根据需要更改数据库文件的名称或路径
current_file_abs_path = Path(__file__).resolve()
print(current_file_abs_path.parent)
# 原 SQLite 配置
# DATABASE_URL = f"sqlite:///{current_file_abs_path.parent}/resource_database.db"

# 改为 MySQL 配置（根据实际情况填写）
DATABASE_URL = "mysql+pymysql://root:123456@192.168.31.201:3306/resource_database"
# 创建数据库引擎
# connect_args={"check_same_thread": False} 是 SQLite 特有的，用于允许多个线程访问数据库
# 如果您在 FastAPI 等异步框架中使用，这是推荐的设置
# 禁用 SQLAlchemy 的日志输出
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
# 先连接到 MySQL 默认库
temp_engine = create_engine("mysql+pymysql://root:123456@192.168.31.201:3306/mysql")

# 创建目标数据库
with temp_engine.connect() as conn:
    conn.execute(text("CREATE DATABASE IF NOT EXISTS resource_database CHARACTER SET utf8mb4"))
engine = create_engine(DATABASE_URL, echo=False, )

def create_db_and_tables():


    print("Creating database and tables...")
    # SQLModel.metadata.create_all 会检查表是否存在，只创建不存在的表
    SQLModel.metadata.create_all(engine)
    print("Database and tables created successfully (if they didn't exist).")

# 如果直接运行此脚本，则创建数据库和表
if __name__ == "__main__":
    create_db_and_tables()