import asyncio

from app.modules.data_collection import flow


class DataCollectionContext:
    def __init__(self,):
        ...

    async def run_hot(self):
        flow_result=await flow.data_collection_get_hot_flow()
        return   flow_result

data_collection_context=DataCollectionContext()



