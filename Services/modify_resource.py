import asyncio
import re

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select, Session

import settings
from QuarkDisk import QuarkDisk
from database import engine
from models.resource import Resource


def modify_risk_handle_status():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where((Resource.has_detect_risk == True))).all()
        for resource in resources:

            for risk_file in resource.risk_file_handle:
                risk_file['status']='downloaded'
            flag_modified(resource, 'risk_file_handle')
            session.add(resource)
        try:
            session.commit()
        except Exception as e:
            print(e)

def modify_risk_handle_skip():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where((Resource.has_detect_risk == True))).all()
        for resource in resources:
            if resource.title=='无忧渡(2025)':
                for risk_file in resource.risk_file_handle:
                    if risk_file['file_name'].endswith('.mp4'):
                        risk_file['status'] = 'downloaded'
                        risk_file.update({'skip_download': False})
                flag_modified(resource, 'risk_file_handle')
                session.add(resource)
        try:
            session.commit()
        except Exception as e:
            print(e)

def modify_resource_has_detect_risk():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where((Resource.has_detect_risk == True))).all()
        for resource in resources:

            resource.has_detect_risk=False
            session.add(resource)
        try:
            session.commit()
        except Exception as e:
            print(e)
def modify_resource_share_handle():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where()).all()
        for resource in resources:
            if not isinstance(resource.share_handle, dict):
                resource.share_handle={}
            resource.share_handle.update({
                'is_skip_share':True
            })
            flag_modified(resource, 'share_handle')
            session.add(resource)
        try:
            session.commit()
        except Exception as e:
            print(e)
async def format_file_name():
    with Session(engine) as session:
        resources = session.exec(select(Resource)).all()
        for resource in resources:
            if resource.title=='淮水竹亭(2025)':
                cloud_storage_path=resource.cloud_storage_path
                quark_disk=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
                fid=await quark_disk.get_fids([cloud_storage_path])
                fid=fid[0]['fid']
                file_list=await quark_disk.ls_dir(fid)
                print(file_list)
                for file in file_list:
                    file_name=file['file_name']
                    fid=file['fid']
                    match = re.search(r'^.*S01E(\d{2}).*(\.mkv)$', file_name)

                    try:
                        if match:
                            part1=match.group(1)
                            part2=match.group(2)
                            new_name=part1+part2
                            print(new_name)
                            await quark_disk.rename(fid,new_name)
                            await asyncio.sleep(2)
                    except Exception as e:
                        print(e)
                return
async def main():
    # modify_risk_handle_status()
    # modify_resource_has_detect_risk()
    # await test()
     modify_resource_share_handle()
    # modify_risk_handle_skip()
if __name__ == '__main__':
    asyncio.run(main())