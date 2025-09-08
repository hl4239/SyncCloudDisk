# 实现
import json
import re
from typing import Optional, List

from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

from app.core.logging_config import get_logger
from app.database.models import OpenAISource
from app.services.interfaces.open_ai_interface import IOpenAIService

logger=get_logger(__name__)
class OpenAIService(IOpenAIService):
    def __init__(self):
        """
        sources: 一个字典，key 是 name，value 是 OpenAISource
        """

    @staticmethod
    async def get_agent( name: str,model:str, instructions: str, tools: Optional[List] = None, output_type: Optional[type] = None) -> Agent:
        source=await OpenAISource.find_one(OpenAISource.name==name )
        if model not in source.models:
            model=source.models[0]
        if source :
            return Agent(
                name='Assistant',
                instructions=instructions,
                model=LitellmModel(
                    model=f"openai/{model}",
                    api_key=source.key,
                    base_url=source.base_url,
                ),
                tools=tools or [],
                output_type=output_type,
            )
    @staticmethod
    def format_to_json(response):
        logger.debug(f'正则格式化：{response}')
        # 1. 去掉三引号包裹
        clean = re.sub(r"^```json|```$", "", response.strip(), flags=re.MULTILINE).strip()
        # 2. 解析 JSON
        data = json.loads(clean)

        # [{'title': '你好', 'season': ''},
        #  {'title': '重启之极海听雷', 'season': '2'},
        #  {'title': '凡人修仙传', 'season': '重返天南'}]
        return data
open_ai_service=OpenAIService()