import logging
import os

from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

import settings


async def get_cookie_str(session):
    # 获取匹配 URL 的 Cookie
    cookies = session.cookie_jar
    # 转换为字典格式
    cookie_dict = {cookie.key: cookie.value for cookie in cookies}
    # 拼接成 "key1=value1; key2=value2" 格式
    cookie_header = "; ".join(f"{key}={value}" for key, value in cookie_dict.items())
    return cookie_header
def get_ai_agent(ins:str,tools:[],cls:type=None):

    return Agent(
        name="Assistant",
        instructions=ins,
        model=LitellmModel(
            model=f'openai/{settings.Current_AI['model']}',
            api_key=settings.Current_AI['key'],
            base_url=settings.Current_AI['url'],
        ),
        tools=tools,
        output_type=cls
    )


# 模块级全局变量
_logger_initialized = False


def setup_logger(log_file: str = "app.log") -> logging.Logger:
    global _logger_initialized

    logger = logging.getLogger("my_logger")

    # 如果已经初始化过，直接返回
    if _logger_initialized:
        return logger

    # 初始化配置
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 Handler
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_file),
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _logger_initialized = True  # 标记为已初始化
    return logger


# 在模块加载时直接初始化
logger = setup_logger()
