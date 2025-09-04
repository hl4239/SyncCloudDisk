# 配置文件加载
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    """
    项目配置类，自动从环境变量或 .env 文件中读取配置
    """
    # model_config 用于指定 Pydantic 的行为
    # env_file = ".env" 表示 Pydantic 会自动查找并加载项目根目录下的 .env 文件
    # 获取项目根目录
    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, ".env"), env_file_encoding='utf-8')

    # --- 数据库配置 ---
    # Pydantic 会自动将大写的环境变量 'DATABASE_URL' 映射到这个同名字段上
    DATABASE_URL: str=Field(default='127.0.0.1:3306')
    # MongoDB 配置
    MONGODB_URI: str = Field(default="mongodb://hl:423999@192.168.31.3/admin")
    MONGODB_DB: str = Field(default="synccloud")
    # --- 日志配置 ---
    LOG_LEVEL: str = "INFO"

    CLOUD_ROOT:str='资源分享'
    TMDB_API_KEY:str=None

# 创建一个全局唯一的配置实例
# 在项目的任何地方，我们都只导入这个 settings 对象
settings = Settings()

# --- 你可以像下面这样方便地进行调试 ---
# if __name__ == "__main__":
#     print(settings.DATABASE_URL)
#     print(settings.model_dump_json(indent=4))