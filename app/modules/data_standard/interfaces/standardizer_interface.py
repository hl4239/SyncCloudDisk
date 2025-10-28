from abc import ABC, abstractmethod
from typing import List, Optional

from app.modules.data_standard.schemas import StandardizedResult



class IStandardizer(ABC):
    @abstractmethod
    async def standardize(cls, items: List[StandardizedResult]) -> List[StandardizedResult]:
        ...
    @classmethod

    async def get_standardized_result(cls,target_original:str,items:List[StandardizedResult])->Optional[StandardizedResult]:
        standardized_results=await cls.standardize(items)
        for result in standardized_results:
            if result.original_name == target_original:
                return result
        return None


