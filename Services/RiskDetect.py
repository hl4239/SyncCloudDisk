import asyncio
import json
import os.path
import random
import re

from sqlmodel import Session, select

import settings
import utils
from QuarkDisk import QuarkDisk
from Services.quark_share_dir_tree import QuarkShareDirTree
from database import engine
from models.resource import Resource, ResourceCategory


class RiskDetect:
    def __init__(self,quark_disk:QuarkDisk):
        self.quark_disk=quark_disk

    async def detect(self,):
        with Session(engine) as session:
            resource_list=session.exec(select(Resource).where((Resource.has_detect_risk==False) & (Resource.category==ResourceCategory.HOT_CN_DRAMA)).order_by(Resource.douban_last_async.desc()).limit(settings.select_resource_num)).all()
            pdir_path_list=[i.cloud_storage_path for i in resource_list]
            get_fids_json=await self.quark_disk.get_fids(pdir_path_list)
            for pdir_list in get_fids_json:
                pdir_fid=pdir_list["fid"]
                pdir_name=pdir_list["file_name"]
                file_info_list=await self.quark_disk.ls_dir(pdir_fid)

                risk_file_info=[i for i in file_info_list if i['risk_type']==2 and i['file_name'].endswith((".mp4", ".mkv"))]


                resource=[i for i in resource_list if i.title==pdir_name][0]
                resource.has_detect_risk=True
                resource.risk_file=risk_file_info
                risk_file_handle=[{
                    'file_name':i['file_name'],
                    'status':'wait_download',
                }for i in risk_file_info
                ]
                resource.risk_file_handle=risk_file_handle

                try:
                    session.add(resource)
                    session.commit()
                except Exception as e:
                    print(e)
                await asyncio.sleep(1)
    @staticmethod
    async def detect_1(src_path:str,share_link:str,quark_disk:QuarkDisk):
        """
        通过查看分享后的链接中缺失的文件被置为风险文件
        :param self:
        :param src_path:
        :param share_link:
        :param quark_disk:
        :return:
        """
        if RiskDetect.is_detected(src_path):
            return
        pdir_fid=(await  quark_disk.get_fids([src_path]))[0]['fid']

        cloud_file_list=await quark_disk.ls_dir(pdir_fid)
        quark_share_dir_tree= QuarkShareDirTree.get_quark_share_tree(share_link)
        await quark_share_dir_tree.parse(max_deep=10)
        share_file_pdir_path=f'/{ os.path.basename(src_path)}'
        share_file_list= quark_share_dir_tree.get_node_info(share_file_pdir_path)
        share_file_name_list=[]
        if  isinstance(share_file_list['child'],list):
            share_file_name_list=[share_file['file_name'] for share_file in share_file_list['child']]
        risk_file_cloud_path_list=[]
        for cloud_file in cloud_file_list:
            file_name=cloud_file['file_name']
            if file_name  not in share_file_name_list:
                risk_file_cloud_path_list.append(file_name)
        await RiskDetect. risk_file_handle(risk_file_cloud_path_list,src_path)
    @staticmethod
    async def risk_file_handle(risk_file_path_list,src_path):
        with Session(engine) as session:
            resource=session.exec(select(Resource).where(Resource.cloud_storage_path==src_path)).all()[0]
            risk_file_handle_list=[
                {
                    'file_name':risk_file_path,
                    'status':'wait_download',
                }
                for risk_file_path in risk_file_path_list
            ]
            resource.has_detect_risk=True
            resource.risk_file_handle=risk_file_handle_list
            session.add(resource)
            try:
                session.commit()
            except Exception as e:
                print(e)

    @staticmethod
    def is_detected(src_path):
        with Session(engine) as session:
            resource = session.exec(select(Resource).where(Resource.cloud_storage_path == src_path)).all()[0]
        return resource.has_detect_risk

    @staticmethod
    async def risk_file_handle_41028(src_path,quark_disk:QuarkDisk):
        if RiskDetect.is_detected(src_path):
            return
        pdir_fid = (await  quark_disk.get_fids([src_path]))[0]['fid']

        cloud_file_list = await quark_disk.ls_dir(pdir_fid)

        risk_file_cloud_path_list = []
        for cloud_file in cloud_file_list:
            file_name = cloud_file['file_name']
            risk_file_cloud_path_list.append(file_name)
        await RiskDetect.risk_file_handle(risk_file_cloud_path_list, src_path)

    @staticmethod
    async def risk_file_handle_41026(src_path,quark_disk:QuarkDisk):
        item_name=os.path.basename(src_path)
        pdir_path=os.path.dirname(src_path)
        item_rename=RiskDetect.rename(item_name)
        new_src_path=f"{pdir_path}/{item_rename}"
        print(f'开始创建文件夹 {new_src_path}' )
        await quark_disk.mkdir(new_src_path)
        print('创建文件夹')
        fid = (await quark_disk.get_fids([src_path]))[0]['fid']
        file_list=await quark_disk.ls_dir(fid)
        fid_file_list=[file['fid']for file in file_list]
        to_pdir_fid=(await quark_disk.get_fids([new_src_path]))[0]['fid']
        try:
            await quark_disk.move(fid_file_list,to_pdir_fid)
        except Exception as e:
            utils.logger.error(f"{src_path} to {new_src_path} failed :{str(e)}")
        try:
            await quark_disk.delete([fid])
        except Exception as e:
            utils.logger.error(f"删除{src_path}失败：{str(e)}")
        with Session(engine) as session:
            resource = session.exec(select(Resource).where(Resource.cloud_storage_path == src_path)).all()[0]
            resource.cloud_storage_path = new_src_path
            session.add(resource)
            try:
                session.commit()
            except Exception as e:
                print(e)

    @staticmethod
    def rename(original_name: str, _retry: int = 0) -> str:
        while _retry <10:
            # 使用正则匹配年份部分（格式为 (YYYY)）
            match = re.search(r"(.*)(\(\d{4}\))$" , original_name.replace(" ", ""))


            name_part=match.group(1)
            year_part=match.group(2)
            print(name_part  ,"||||",year_part)
            # 如果名称部分长度不足3，无法插入2个空格，直接返回
            if len(name_part) < 3:
                return name_part + year_part

            # 随机选择2个不同的位置插入空格（确保不重复）
            positions = sorted(random.sample(range(1, len(name_part)), 2))

            # 构建新名称（在选定位置插入空格）
            new_name = (
                    name_part[:positions[0]] + " " +
                    name_part[positions[0]:positions[1]] + " " +
                    name_part[positions[1]:]
            )
            # 最终仍相同则强制修改
            if new_name + year_part != original_name:
                return new_name + year_part





async def main():
    # quark_disk=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    # risk_detect = RiskDetect(quark_disk)
    # # await risk_detect.detect()
    # await risk_detect.detect_1('/资源分享/热门-国产剧/淮水竹 亭(2025)','https://pan.quark.cn/s/73fdaafee5ef#/list/share',quark_disk)
    # await quark_disk.connect()
    # await quark_disk.close()
    result=  RiskDetect.rename('dasdsadasosdao(1234)')
    print(result)
if __name__ == '__main__':
    asyncio.run(main())