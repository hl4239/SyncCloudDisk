import copy
import functools
from typing import Type, Any, Dict
from agents import Runner, function_tool
from utils import get_ai_agent


class CallAI:
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
            print(output_model)
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
        agent = get_ai_agent(instruction, tools)

        result = await Runner.run(agent, input=input)
        output = CallAI.get_output()
        if output is not None:
            pass
        else:
            raise Exception(f'结构化输出失败,{result.final_output}')
        return output,result.final_output