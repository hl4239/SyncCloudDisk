from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import httpx

# 创建 MCP 服务器实例
mcp = FastMCP("Demo Server")

# 添加资源
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """获取个性化问候语"""

    return f"你好, {name}!"

# 添加工具
@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """计算BMI指数"""
    return round(weight_kg / (height_m ** 2), 2)

@mcp.tool()
async def fetch_weather(city: str) -> str:
    """
    获取城市的天气
    :param city: 城市名
    :return: 城市的天气报告
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "3"},
                headers={"User-Agent": "curl/7.68.0"}
            )
            return response.text.strip()
        except Exception as e:
            return f"获取天气失败: {str(e)}"

# 添加提示
@mcp.prompt()
def review_code(code: str) -> str:
    """代码审查提示"""
    return f"请审查以下代码:\n\n{code}"

if __name__ == "__main__":
    mcp.run()