# 实现
import asyncio
import json
import re
from typing import Optional, List

from agents import Agent, ModelSettings, Runner
from agents.extensions.models.litellm_model import LitellmModel
from litellm.llms.openai.openai import OpenAIConfig

from app.core.logging_config import get_logger
from app.database.database import init_db
from app.database.models import OpenAISource, SystemConfig
from app.services.interfaces.open_ai_interface import IOpenAIService

logger=get_logger(__name__)
class OpenAIService(IOpenAIService):
    def __init__(self):
        """
        sources: 一个字典，key 是 name，value 是 OpenAISource
        """
    @classmethod
    def _get_agent(cls,instructions,model,key,base_url,extra_body,tools,output_type):
        model_settings = ModelSettings(
                extra_body=extra_body,
            ) if extra_body else None
        print(instructions,model,key,base_url,extra_body,tools,output_type)
        return Agent(
            name='Assistant',
            instructions=instructions,
            model=LitellmModel(
                model=f"openai/{model}",
                api_key=key,
                base_url=base_url,
            ),
            model_settings=model_settings,  # 添加 model_settings
            tools=tools or [],
            output_type=output_type,
        )

    @classmethod
    async def get_agent(cls,
            name: Optional[str]=None,
            model: Optional[str]=None,
            instructions: Optional[str]=None,
            tools: Optional[List] = None,
            output_type: Optional[type] = None,

    ) -> Optional[Agent]:
        system_config = await SystemConfig.find_one()
        if name is None:

            name=system_config.open_ai_config.default_source_name
        source=None
        for i in system_config.open_ai_config.sources:
            if i.name == name:
                source=i
        if not source  and system_config.open_ai_config.sources:
            source=system_config.open_ai_config.sources[0]
        if not source:

            return None
        if not model or model not in source.models:
            model = source.models[0]
        if source:
            return cls._get_agent(instructions=instructions,key=source.key,model=model,base_url=source.base_url,extra_body=source.extra_body,tools=tools,output_type=output_type)


    @staticmethod
    def format_to_json(response):
        logger.debug(f'正则格式化：{response}')
        # 1. 去掉三引号包裹
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", response, flags=re.DOTALL | re.IGNORECASE)
        if m:
            clean = m.group(1)  # code fence 里的内容（首尾空白被剔除）
        else:
            clean = response.strip()
        # 2. 解析 JSON
        data = json.loads(clean)

        # [{'title': '你好', 'season': ''},
        #  {'title': '重启之极海听雷', 'season': '2'},
        #  {'title': '凡人修仙传', 'season': '重返天南'}]
        logger.debug(f'提取json为：{data}')
        return data
open_ai_service=OpenAIService()

async def main():
    await init_db()
    agent=await open_ai_service.get_agent(instructions='你好')
    result = await Runner.run(agent,
                              input=f'你好,你是？')
    print(result.final_output)
    # r= open_ai_service.format_to_json('')

if __name__ == '__main__':
    asyncio.run(main())