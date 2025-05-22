import asyncio
import json
import os

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select
import settings
import utils
from QuarkDisk import QuarkDisk
from Services.alist_api import AlistAPI
from Services.quark_share_dir_tree import QuarkShareDirTree
from Services.risk_handle import RiskHandle
from database import engine
from models.resource import Resource, ResourceCategory


class CreateShareLink:
    def __init__(self,quark_disk_list:[QuarkDisk],risk:RiskHandle):
        self.quark_disk_list = quark_disk_list
        self.default_quark_disk = quark_disk_list[0]
        self.other_quark_disks = quark_disk_list[1:]
        self.risk = risk

    @staticmethod
    async def save_from_share(quark_share_dir_tree:QuarkShareDirTree,src_path,save_pdir:str,quark_disk:QuarkDisk):
        """
        转存分享链接中的文件
        :param quark_share_dir_tree: 遍历分享链接的对象
        :param src_path: 被转存的文件
        :param save_pdir: 转存到的父目录
        :param quark_disk: 被转存的quark对象
        :return:
        """
        share_file = quark_share_dir_tree.get_node_info(f'{src_path}')
        share_file_fid = share_file['fid']
        print(share_file)
        share_file_token = share_file['share_fid_token']
        try:
            save_path=f'{save_pdir}{src_path}'
            resp=  await quark_disk.get_fids([save_path])
            fid=resp[0]['fid']
            await quark_disk.delete([fid])
        except Exception as e:
            pass

        try:
            resp=  await quark_disk.get_fids([save_pdir])
            pdir_fid=resp[0]['fid']
        except Exception as e:
            await quark_disk.mkdir(save_pdir)
            resp = await quark_disk.get_fids([save_pdir])
            pdir_fid = resp[0]['fid']

        pwd_id=quark_share_dir_tree.ParseQuarkShareLInk.pwd_id
        stoken=quark_share_dir_tree.ParseQuarkShareLInk.stoken
        try:
            return await quark_disk.save_file([share_file_fid],  fid_token_list=[share_file_token], to_pdir_fid=pdir_fid,stoken=stoken,pwd_id=pwd_id)
        except Exception as e:
            raise e
    @staticmethod
    def save_to_database(result_share_list:[]):
        with Session(engine) as session:
            resources = session.exec(select(Resource).where()).all()
            resource_map={
                resource.cloud_storage_path:resource
                for resource in resources
            }
            print(result_share_list)
            for resource in resource_map.values():
                if resource.share_handle is None:
                    resource.share_handle={}
                share_handle=resource.share_handle

                share_handle.update({'share_list':[]})
            for result_share in result_share_list:
                src_path = result_share['src_path']
                resource=resource_map.get(src_path)
                share_handle=resource.share_handle
                share_list=share_handle.get('share_list',[])
                share_list.append(result_share)
                share_handle.update({'share_list':share_list})

            for resource in resources:
                flag_modified(resource,'share_handle')
                session.add(resource)
            try:
                session.commit()
            except Exception as e:
                print(e)



    @staticmethod
    async def save_and_craete_link(quark_share_dir_tree:QuarkShareDirTree,src_path,save_pdir:str,quark_disk:QuarkDisk):
        try:
           if await CreateShareLink.save_from_share(quark_share_dir_tree=quark_share_dir_tree,src_path=src_path,save_pdir=save_pdir,quark_disk=quark_disk):
               fid=(await quark_disk.get_fids([f'{save_pdir}{src_path}']))[0]['fid']
               return await quark_disk.create_share_link([fid],title='')
        except Exception as e:
            raise
    async def _save_and_craete_link(self,quark_share_dir_tree:QuarkShareDirTree,src_path,save_pdir:str,quark_disk:QuarkDisk):
        result={
               'src_path':f"{save_pdir}{src_path}" ,
               'account':quark_disk.name,
           }
        try:
           result.update({'share_link':await CreateShareLink.save_and_craete_link(quark_share_dir_tree, src_path, save_pdir,quark_disk=quark_disk)})

        except Exception as e:
            result.update({'exception':str(e)})
        return result
    async def zhuancun(self):
        with Session(engine) as session:
            statement = select(Resource).where(Resource.category == ResourceCategory.HOT_CN_DRAMA).order_by(
                Resource.douban_last_async.desc()).limit(settings.select_resource_num)
            resources = session.exec(statement).all()


            for resource in resources:
                if resource.share_handle is None:
                    resource.share_handle ={}
                    session.add(resource)
            resources = [
                resource for resource in resources
                if getattr(resource, 'share_handle', None)==None
                   or resource.share_handle.get('is_skip_share', False) ==False
            ]

        resource_map={
            resource.cloud_storage_path:resource
            for resource in resources
        }
        if len(resource_map.items())==0:
            return
        path_list = [resource.cloud_storage_path for resource in resources]
        resp_json=await self.default_quark_disk.get_fids(path_list)
        print(resp_json)
        share_results=[]
        for resp in resp_json:
            file_path=resp["file_path"]
            pdir_file_path=os.path.dirname(file_path)
            resource=resource_map[resp['file_path']]
            share_file_name=os.path.basename(file_path)
            fid=resp['fid']
            try:
                share_list= resource.share_handle.get('share_list',[])
                default_share_link=None
                for share in share_list:
                    if share['account'] == self.default_quark_disk.name:
                        default_share_link=share.get('share_link',None)

                        break
                if default_share_link is None:
                    default_share_link = await self.default_quark_disk.create_share_link([fid],title='')
                else:
                    try:
                        quark_share_dir_tree = QuarkShareDirTree.get_quark_share_tree(default_share_link)
                        await quark_share_dir_tree.parse()
                        print(f'延用可用的分享链接：{default_share_link}')
                    except Exception as e:
                        default_share_link = await self.default_quark_disk.create_share_link([fid], title='')
                        print(f'链接失效，重新创建:{default_share_link}')


                share_results.append({
                    'src_path': file_path,
                    'account': self.default_quark_disk.name,
                    'share_link': default_share_link
                })


            except Exception as e:
                share_results.append({
                    'src_path': file_path,
                    'account': self.default_quark_disk.name,
                    'exception': str(e)
                })
                utils.logger.error(e)
                try:

                    e_json= json.loads(str(e))
                    message=e_json['message']
                    code=e_json['code']
                    src_path = resource.cloud_storage_path

                    if code==41028:
                        await self.risk.risk_file_handle_41028(resource.storage_path,src_path,self.default_quark_disk)
                        pass
                    elif code==41026:
                        await self.risk.risk_file_handle_41026(src_path, self.default_quark_disk)
                except Exception as e:
                    pass
                continue
            await self.risk.detect_1(resource.storage_path,file_path,default_share_link,self.default_quark_disk)
            quark_share_dir_tree=QuarkShareDirTree.get_quark_share_tree(default_share_link)
            await quark_share_dir_tree.parse()
            tasks=[
             self._save_and_craete_link(quark_share_dir_tree,src_path=f'/{share_file_name}',save_pdir=pdir_file_path,quark_disk=other_quark_disk)
                for other_quark_disk in self.other_quark_disks
            ]
            task_results=  await asyncio.gather(*tasks)
            for idx, result in enumerate(task_results):

                share_results.append(result)

        share_results_str=json.dumps(share_results,ensure_ascii=False,indent=4)
        self.save_to_database(share_results)
        utils.logger.info(f"---------------分享链接----------------：\n{share_results_str}")


        # default_share_link_list=[await self.default_quark_disk.create_share_link(f['fid']) for f in resp_json]
        # for share_link in default_share_link_list:
        #     if share_link is None:
        #
        # logger.info(default_share_link_list)
        # print(resp_json)



async def main():
    # quark_disk_list=[QuarkDisk(setting) for setting in settings.STORAGE_CONFIG['quark']]
    quark_disk_list=[QuarkDisk(settings.STORAGE_CONFIG['quark'][0])]
    alist=AlistAPI()
    risk=RiskHandle(alist)
    create_share_link=CreateShareLink(quark_disk_list,risk)
    await create_share_link.zhuancun()
    for quark_disk in quark_disk_list:
        await quark_disk.close()


    await QuarkShareDirTree.close()
if __name__ == '__main__':
    asyncio.run(main())