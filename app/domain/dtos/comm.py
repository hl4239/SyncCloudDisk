from typing import Optional, Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """通用的API响应封装"""
    success: bool = True
    message: str
    data: Optional[Any] = None