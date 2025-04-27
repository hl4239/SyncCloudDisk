from sqlmodel import SQLModel, create_engine
from models.resource import Resource # 确保从正确的路径导入 Resource 模型

# 定义 SQLite 数据库文件路径
# 您可以根据需要更改数据库文件的名称或路径
DATABASE_URL = "sqlite:///./resource_database.db"

# 创建数据库引擎
# connect_args={"check_same_thread": False} 是 SQLite 特有的，用于允许多个线程访问数据库
# 如果您在 FastAPI 等异步框架中使用，这是推荐的设置
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """
    创建数据库文件和定义的表（如果它们不存在）。
    """
    print("Creating database and tables...")
    # SQLModel.metadata.create_all 会检查表是否存在，只创建不存在的表
    SQLModel.metadata.create_all(engine)
    print("Database and tables created successfully (if they didn't exist).")

# 如果直接运行此脚本，则创建数据库和表
if __name__ == "__main__":
    create_db_and_tables()