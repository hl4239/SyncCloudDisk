import asyncio

from app.modules.data_collection.container import DataCollectionContainer


class DataCollectionContext:
    def __init__(self,container:DataCollectionContainer):
        self.container=container

    async def run_hot(self):
        pipe=self.container.data_collection_pipelines
        return   await pipe.run_hot()





