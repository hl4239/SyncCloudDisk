import asyncio
from typing import List


from app.core.abc_aio_client import  BaseAioClient
from app.database.models import CloudType


class PanSouClient(BaseAioClient):
    def __init__(self):
        super().__init__()
        super().init(
            "pansou",
            base_url="http://192.168.31.3:8083/",
            headers={
                "User-Agent": "PanSouBot/1.0",

            }
        )
    @classmethod
    def _convert_cloud_types(cls,cloud_types:List[CloudType]):
        result=[]
        for cloud_type in cloud_types:
            if cloud_type==CloudType.QUARK:
                result.append('quark')
            if cloud_type==CloudType.BAIDU:
                result.append('baidu')
        return result

    async def search(self, keyword:str,cloud_types:List[CloudType],refresh:bool=True) -> dict:
        params ={
                  "kw": keyword,
                  "cloud_types": self._convert_cloud_types(cloud_types),
            "refresh":True
                }
        return await self.fetch_json( "POST", "/api/search", json=params)
pan_sou_client = PanSouClient()
async def main():

    result=await pan_sou_client.search('赴山海',[CloudType.BAIDU])
    print(result)
if __name__ == '__main__':
    asyncio.run(main())

