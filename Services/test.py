import asyncio

from agents import function_tool
from pydantic import BaseModel

from Services.call_ai import CallAI


class Weather(BaseModel):
    city: str
    temperature: float
@function_tool
def query_weather(city):
    """
    查询天气
    :param city:城市名
    :return:
    """
    print('asdasd=-------------')
    return '16.8度'

async def main():
    result=await CallAI.ask('你是一位天气助手',input='南京的气温',tools=[query_weather],format_output=Weather)
if __name__ == '__main__':
    asyncio.run(main())