import asyncio
import json

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from openai import OpenAI

import settings


async def run_client():
    # 配置服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["server-example.py"]
    )

    # 创建客户端
    client = OpenAI(
        api_key=settings.Current_AI['key'],
        base_url=settings.Current_AI['url'],  # 确保末尾不要带 /
    )
    # List the files it can read
    message = "Read the files and list them."
    print(f"Running: {message}")



    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            print("连接已建立")
            # 列出可用工具
            print("\n尝试获取工具列表...")
            response = await session.list_tools()

            if response:
                print("\n可用工具:")

                print('----------------tools----------------------')
                print(response)
                available_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object",  # 修复点：必须是 object，而不是 int
                                "properties": {
                                    key: {
                                        'type':value['type'],
                                         "description": value['title']
                                    } for key ,value in tool.inputSchema['properties'].items()
                                },
                                "required":tool.inputSchema['required'],
                            }
                        }
                    }
                    for tool in response.tools
                ]
                print(available_tools)
                message=[

                ]
                question= input('请输入问题：')

                message.append({"role": "user", "content": f"{question}"})
                print(json.dumps(message,indent=4))
                response=  client.chat.completions.create(
                                                        model=settings.Current_AI['model'],
                                                        messages=message,
                                                        tools=available_tools,

                                                         )
                print(response.to_json())
                while response.choices[0].finish_reason!='stop':
                    message.append(response.choices[0].message)
                    if response.choices[0].finish_reason=='tool_calls':
                        for call_ in response.choices[0].message.tool_calls:
                            call_name = call_.function.name
                            args=json.loads( call_.function.arguments)
                            # Call a tool
                            result = await session.call_tool(call_name, args)
                            message.append({"role": "tool", "tool_call_id": call_.id,'content': f"{result}"})
                    response=client.chat.completions.create(
                        model=settings.Current_AI['model'],
                        messages=message,
                        tools=available_tools,
                    )
                print(response.to_json())
                message.append(response.choices[0].message)





if __name__ == "__main__":
    asyncio.run(run_client())