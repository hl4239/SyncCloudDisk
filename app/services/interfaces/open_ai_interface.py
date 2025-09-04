from abc import ABC, abstractmethod
from typing import Optional, List

from agents import Agent


class IOpenAIService(ABC):

    @staticmethod
    @abstractmethod
    async def get_agent( name: str,model:str, instructions: str, tools: Optional[List] = None, output_type: Optional[type] = None) -> Agent:
        ...

    @staticmethod
    def format_to_json(response):
        ...