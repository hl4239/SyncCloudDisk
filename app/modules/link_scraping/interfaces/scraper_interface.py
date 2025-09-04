from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from app.modules.link_scraping.schemes.link import ResourceLink, LinkType


class ILinkScraper(ABC):

    @abstractmethod
    async def search(
            self,
            title: str,
            link_types: Optional[Sequence[LinkType]] = None
    ) -> List[ResourceLink]:
        """
        根据标题搜索资源链接。

        :param title: 要搜索的影视标题。
        :param link_types: 指定要搜索的网盘类型列表。如果为 None，则搜索所有支持的类型。
        :return: 一个包含所有找到的 ResourceLink 对象的列表。如果找不到，则返回一个空列表。
        """
        # ... 实现逻辑 ...
        # 即使一个都没找到，也应该返回 []
        # return found_links