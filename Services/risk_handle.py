import asyncio
import os
import random
import re
from pathlib import Path, PurePosixPath

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

import settings
import utils
from QuarkDisk import QuarkDisk
from Services.alist_api import AlistAPI
from Services.quark_share_dir_tree import QuarkShareDirTree
from Services.video_edit import VideoMetadataEditor
from database import engine
from models.resource import Resource


class RiskHandle:
    def __init__(self,alist:AlistAPI):
        self.alist = alist
        self.local_base='/downloads'
        self.cloud_base='/夸克网盘'
    async def add_copy(self,src_path,dst_path,file_name_list,base_src,base_dst):
        """

        :param src_path: 无需加self.local_base
        :param dst_path: 无需加self.cloud_base
        :param file_name_list:
        :param base_src:
        :param dst_src:
        :return:
        """
        result= await self.alist.copy([
            {
                'src_path':f'{src_path}/{f}',
                'dst_pdir_path':dst_path,
            }
            for f in file_name_list
        ],base_src,base_dst)




    async def get_dir(self,path,ensure_exist=False):
        """

        :param path: /downloads/xxx
        :param ensure_exist:
        :return:
        """
        # 返回目录文件，不存在则创建
        try:
            local_files = await self.alist.ls_dir(path)
            if local_files is None:
                local_files = []
        except Exception as e:
            if ensure_exist:
                await self.alist.mkdir(path)
                local_files = []

        return local_files


    async def get_undone_copy_file_names(self,path):

        """
        获取正在复制的文件名
        :param path: :/downloads/xxx,为拷贝的目标目录
        :return: undone_path_files
        """
        undone_files= await self.alist.get_copy_undone_tasks()
        undone_path_files=[]
        for file in undone_files:
            dst_path=file['dst_path']
            src_path=file['src_path']
            if dst_path==path:
                file_name= Path(src_path).name
                undone_path_files.append(file_name)


        return undone_path_files

    async def modify_hash(self,storage_path_list):
        """

        :param storage_path_list: /资源分享/xxx
        :return:
        """
        for storage_path in storage_path_list:
            VideoMetadataEditor.modify_hash(storage_path)

    async def risk_handle(self,local_path,cloud_path,file_name_list):
        """
        判断本地是否存在文件，如果不存在则下载，存在则判断是否有相同的正在上传的，如果不存在则修改hash并上传
        :param local_path: /资源分享   不用包含/downloads
        :param cloud_path: /资源分享/xxx 不用包含/夸克网盘
        :param file_name_list:
        :return:
        """
        # alist上传时会对被覆盖的文件改名为.alist_to_delete，因此要过滤
        file_name_list=[file_name for file_name in file_name_list if file_name.endswith('.alist_to_delete')==False]
        if len(file_name_list) > 0:
            local_files=await self.get_dir(f'{self.local_base}{local_path}',ensure_exist=True)
            cloud_files=await self.get_dir(f'{self.cloud_base}{cloud_path}')

            local_file_names=[f['name'] for f in local_files]
            need_download_file_names = [f for f in file_name_list if f not in local_file_names]
            downloading_file_names=await self.get_undone_copy_file_names(self.local_base+local_path)
            downloaded_file_names=list(set(local_file_names) - set(downloading_file_names))
            uploading_file_names=await self.get_undone_copy_file_names(self.cloud_base+cloud_path)
            need_modify_file_names=[f for f in downloaded_file_names if f in file_name_list and f not in uploading_file_names ]
            if len(need_download_file_names)>0:
                await self.add_copy(src_path=cloud_path,dst_path=local_path,file_name_list=need_download_file_names,base_src=self.cloud_base,base_dst=self.local_base)
            if len(need_modify_file_names)>0:
                await self.modify_hash([f'{local_path}/{file_name}' for file_name in need_modify_file_names])
                await self.add_copy(src_path=local_path, dst_path=cloud_path, file_name_list=need_modify_file_names,base_src=self.local_base, base_dst=self.cloud_base)

            downloading_file_names=await self.get_undone_copy_file_names(self.local_base+local_path)
            uploading_file_names = await self.get_undone_copy_file_names(self.cloud_base + cloud_path)

            utils.logger.info(f'处理这些风险文件:{file_name_list} | '
                                  f'正在下载：{downloading_file_names} | '
                                  f'已修改并正在上传：{uploading_file_names}')

    async def risk_file_handle_41028(self, storage_path, cloud_path, quark_disk: QuarkDisk):
        """大部分资源都为风险，则删除所有文件"""
        # if RiskDetect.is_detected(src_path):
        #     return
        pdir_fid = (await  quark_disk.get_fids([cloud_path]))[0]['fid']

        cloud_file_list = await quark_disk.ls_dir(pdir_fid)
        file_name_list=[f['file_name'] for f in cloud_file_list]
        await self.risk_handle(storage_path, cloud_path,file_name_list )

    async def risk_file_handle_41026(self, src_path, quark_disk: QuarkDisk):
        """
        处理文件夹命名导致的风险
        :param src_path:
        :param quark_disk:
        :return:
        """
        item_name = os.path.basename(src_path)
        pdir_path = os.path.dirname(src_path)
        item_rename = RiskHandle.rename(item_name)
        new_src_path = f"{pdir_path}/{item_rename}"
        await quark_disk.mkdir(new_src_path)
        fid = (await quark_disk.get_fids([src_path]))[0]['fid']
        file_list = await quark_disk.ls_dir(fid)
        fid_file_list = [file['fid'] for file in file_list]
        to_pdir_fid = (await quark_disk.get_fids([new_src_path]))[0]['fid']
        try:
            await quark_disk.move(fid_file_list, to_pdir_fid)
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

    async def detect_1(self, storage_path, cloud_src_path: str, share_link: str, quark_disk: QuarkDisk):
        """
        通过查看分享后的链接中缺失的文件被置为风险文件

        :param cloud_src_path:
        :param share_link:
        :param quark_disk:
        :return:
        """
        # if RiskDetect.is_detected(cloud_src_path):
        #     return
        pdir_fid = (await  quark_disk.get_fids([cloud_src_path]))[0]['fid']

        cloud_file_list = await quark_disk.ls_dir(pdir_fid)
        quark_share_dir_tree = QuarkShareDirTree.get_quark_share_tree(share_link)
        await quark_share_dir_tree.parse(max_deep=10)
        share_file_pdir_path = f'/{os.path.basename(cloud_src_path)}'
        share_file_list = quark_share_dir_tree.get_node_info(share_file_pdir_path)
        share_file_name_list = []
        if isinstance(share_file_list['child'], list):
            share_file_name_list = [share_file['file_name'] for share_file in share_file_list['child']]
        risk_file_cloud_list = []
        for cloud_file in cloud_file_list:
            file_name = cloud_file['file_name']
            if file_name not in share_file_name_list:
                risk_file_cloud_list.append(file_name)

        await self.risk_handle(storage_path, cloud_src_path,risk_file_cloud_list )

    @staticmethod
    def rename(original_name: str, _retry: int = 0) -> str:
        while _retry < 10:
            # 使用正则匹配年份部分（格式为 (YYYY)）
            match = re.search(r"(.*)(\(\d{4}\))$", original_name.replace(" ", ""))

            name_part = match.group(1)
            year_part = match.group(2)
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
    alist=AlistAPI()
    risk_detect = RiskHandle(alist)
    quark_disk=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])

    await    risk_detect.risk_handle('/资源分享','/资源分享',['A.Better.Life.S01E28.2025.2160p.WEB-DL.H265.AAC_2.mp4.alist_to_delete'])
if __name__ == '__main__':
    asyncio.run(main())