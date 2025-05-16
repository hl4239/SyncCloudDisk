import asyncio
import json

from sqlmodel import Session, select

import utils
from database import engine
from models.resource import Resource


def print_share_link():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where()).all()
    share_link_list = []
    for resource in resources:
        if resource.share_handle.get('share_list'):
            share_list = resource.share_handle.get('share_list')
            for share in share_list:
                if share.get('share_link'):
                    share_link_list.append(share)
    print(json.dumps(share_link_list, indent=4,ensure_ascii=False))

async def main():
    print_share_link()
    utils.logger.info('xczcczx')
if __name__ == '__main__':
    asyncio.run(main())