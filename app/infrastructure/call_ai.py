import copy
import functools
import logging
from typing import Type, Any, Dict
from agents import Runner, function_tool, Agent
from agents.extensions.models.litellm_model import LitellmModel

from app.infrastructure.config import settings

logger=logging.getLogger()
class CallAI:
    @staticmethod
    def get_ai_agent(ins: str, tools: [], cls: type = None):
        default_ai_config=settings.ai.config_dict[settings.ai.default]

        return Agent(
            name="Assistant",
            instructions=ins,
            model=LitellmModel(
                model=f'openai/{default_ai_config.model}',
                api_key=default_ai_config.key,
                base_url=default_ai_config.url,
            ),
            tools=tools,
            output_type=cls
        )

    output_result = None

    @staticmethod
    def get_output():
        if CallAI.output_result is not None:
            result = copy.deepcopy(CallAI.output_result)
            CallAI.output_result = None
            return result

    @classmethod
    def set_output_type(cls, output_type: Type):
        """动态设置output方法的参数类型并添加function_tool注解"""

        def output(output_model: output_type):
            cls.output_result = output_model

            return '已成功输出,结束对话'


        # 添加类型注解
        output.__annotations__ = {'output_model': output_type}

        # 添加function_tool注解
        output = function_tool(output)

        # 替换原来的output方法
        cls.output = staticmethod(output)


    @staticmethod
    async def ask(instruction: str, input: str, tools: list, format_output: type):
        # 动态设置output方法的参数类型
        CallAI.set_output_type(format_output)

        tools.append(CallAI.output)
        if format_output is not None:
            instruction='You will call the {output} tool to deliver the final result.'+ instruction
        agent = CallAI.get_ai_agent(instruction, tools)

        result = await Runner.run(agent, input=input)
        output = CallAI.get_output()
        if output is not None:
            pass
        else:
            raise Exception(f'结构化输出失败,{result.final_output}')
        logger.debug(f'调用ai结果：{output} |  {result.final_output}')
        return output,result.final_output