import asyncio
import logging

from app.domain.models.cloud_file import ShareParseInfo, QuarkShareParseInfo, QuarkShareFile, ShareFile, CloudFile
from app.infrastructure.cloud_storage.providers.quark_cloud_api import QuarkCloudAPI, ParseQuarkShareLInk
from app.services.cloud_file_service import CloudFileService
from app.services.episode_normalize_service import EpisodeNormalizeService

logger=logging.getLogger()
class CloudShareService(CloudFileService):
    def __init__(self,normalize_service: EpisodeNormalizeService,):
        # 对应分享链接的根节点cloud_file
        super().__init__(normalize_service)
        self.cloud_share_file_dict = {}
        self.normalize_service=normalize_service
        self._share_lock=asyncio.Lock()
        ...

    @staticmethod
    async def quark_parse(share_link:str):
        parse = ParseQuarkShareLInk(share_link)
        await parse.parse_share_link()
        share_parse_info = QuarkShareParseInfo()
        root_share_file = QuarkShareFile()
        root_share_file.file_name='/'
        root_share_file.file_type=0
        root_share_file.fid=parse.pdir_fid
        root_share_file.pdir_path=''
        root_share_file.children=None

        async def _traverse_dir(current_deep, max_deep, pdir_fid):
            max_deep_reached_msg_template = "请增加max_deep以查看此目录,current_deep={cd},max_deep={md}"

            if current_deep > max_deep:
                return None

            file_detail_list_response = await parse.ls_dir(pdir_fid)
            if not file_detail_list_response or 'list' not in file_detail_list_response:
                raise Exception(
                    f"Warning: ls_dir for fid {pdir_fid} returned an unexpected response,可能为链接已失效: {file_detail_list_response}")

            file_detail_list = file_detail_list_response['list']
            if len(file_detail_list) == 0:
                return []
            result=[]
            for file_detail in file_detail_list:
                share_file=QuarkShareFile(
                    fid= file_detail['fid'],
                file_name= file_detail['file_name'],
                file_type= file_detail['file_type'],
                pdir_fid= file_detail['pdir_fid'],
                share_fid_token= file_detail['share_fid_token'],
                )
                if share_file.file_type==0:
                    share_file.children=await _traverse_dir(current_deep+1,max_deep,share_file.fid)
                result.append(share_file)
            return result
        try:
            root_share_file.children=await _traverse_dir(0,99,root_share_file.fid)
            share_parse_info.is_valid = True
            share_parse_info.root = root_share_file
            share_parse_info.pwd_id = parse.pwd_id
            share_parse_info.stoken = parse.stoken
            share_parse_info.pdir_fid = parse.pdir_fid
            share_parse_info.share_link = share_link
            share_parse_info.passcode = parse.passcode
        except Exception as e:
            share_parse_info.is_valid=False
            logger.debug(f'解析资源链接{share_link},error:{e}')

        await parse.close()
        return share_parse_info

    async def _parse(self,share_link:str):
        """

        :param share_link:
        :param is_normalize: 是否对影视文件名标准
        :return:
        """
        logger.debug(f'正在解析分享链接：share_link={share_link}')
        result=None
        if 'quark' in share_link:
            result=await CloudShareService.quark_parse(share_link)

        if result is not None:
            self.cloud_share_file_dict.update({
                share_link:result
            })


        logger.debug(f'解析分享链接share_link={share_link}成功，is_valid={result.is_valid}')



        return result

    async  def get_parse_info(self,share_link:str,refresh=False,is_normalize:bool=False):
        async with self._share_lock:
            result=None
            logger.debug(f'正在获取分享链接的解析信息：share_link={share_link}')
            if refresh or self.cloud_share_file_dict.get(share_link,None) is None:

                parse_info=await self._parse(share_link)
                result= parse_info
            else:
                p=self.cloud_share_file_dict.get(share_link)
                logger.debug(f'已从缓存中得到share_link={share_link}')
                result= p

            if is_normalize and result.is_valid:
                root = result.root
                cloud_files = root.flatten()
                movie_files = self.get_movie_files(cloud_files)

                await self.normalize_episode(movie_files)

        return result














