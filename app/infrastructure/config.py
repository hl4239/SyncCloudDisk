# app/core/config.py
import enum
from typing import Dict, Optional
import yaml
from pydantic import BaseModel, Field
from pathlib import Path

CONFIG_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"

class CloudAPIType(str, enum.Enum):
    QUARK='quark'


class CloudAPIConfig(BaseModel):
    cookies:str
    name:str
    type:CloudAPIType

class AIServiceConfig(BaseModel):
    url: str
    key: str
    model: str
    type: Optional[str] = None


class AISettings(BaseModel):
    default: str
    config_dict: Dict[str, AIServiceConfig] = Field(default_factory=dict)


class DatabaseSettings(BaseModel):
    url: Optional[str] = None
    echo: bool = False


class Settings(BaseModel):
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings
    cloud_api: list[CloudAPIConfig]
    cloud_base_path:str=Field(default=None)
    share_link_crawl_count:int=1
    select_resource_count:int=20

def load_config(path: Path = CONFIG_FILE_PATH) -> Settings:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found at {path}")

    with open(path, 'r',encoding='utf-8') as f:
        config_data = yaml.safe_load(f) or {}

    # Handle missing sections with defaults
    if 'database' not in config_data:
        config_data['database'] = {}
    if 'ai' not in config_data:
        raise ValueError("AI configuration section is required in config.yaml")

    return Settings(**config_data)

settings=load_config()


# 示例用法
if __name__ == "__main__":
    print(f"Default AI Provider: {settings.ai.default}")
    print(f"Available AI Services: {list(settings.ai.list.keys())}")
    print(f"DeepSeek Config: {settings.ai.list['deepseek'].model}")