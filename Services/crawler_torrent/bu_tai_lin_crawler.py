import asyncio
import json
from typing import Optional

import aiohttp

import Services.crawler_torrent.crawler
from Services.crawler_torrent.crawler import SearchResult, ResourceType
from Services.episode_namer_dir.bu_tai_lin_episode_namer import BuTaiLinEpisodeNamer


class BuTaiLinCrawler:
    def __init__(self):
        self.session=aiohttp.ClientSession()
        self.app_id='83768d9ad4'
        self.identity='23734adac0301bccdcb107c4aa21f96c'
        self.base_url='https://www.3bt0.com'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
        }
    async def request(self,method:str,url:str,*,params=None,data=None,json=None,headers=None):
        params.update({
            'app_id':self.app_id,
            'identity':self.identity,
        })
        if headers is None:
            headers={}
        headers.update(self.headers)
        result=await self.session.request(method,url,params=params,data=data,json=json,headers=headers)
        return result

    async def _search(self,title):
        url=self.base_url+'/prod/api/v1/getVideoList'
        params={
            'sb':title,
            'page':1,
            'limit':24,
        }
        async with await self.request(method='get',url=url,params=params) as resp:
            resp_json=await resp.json()
            return resp_json

    async def parse_search(self,json):
        if json['message']!='请求成功':
            raise Exception(f'不太冷搜索发生错误：{json["message"]}')
        search_data_list=json['data']['data']
        return search_data_list

    async def get_detail(self,idcode):
        url=self.base_url+'/prod/api/v1/getVideoDetail'
        params={
            'id':idcode,
        }
        async with await self.request(method='get',url=url,params=params) as resp:
            resp_json=await resp.json()
            return resp_json



    async def parse_detail(self,json):
        if json['message'] != '请求成功':
            raise Exception(f'不太冷资源详情发生错误：{json["message"]}')
        search_data_list = json['data']

        return search_data_list

    def select_data(self,data_list,title,year):
        for data in data_list:
            title_=data['title']
            year_=data['years']
            if year_==year:
                return data
        raise f'未找到匹配的资源：{title} {year}'


    async def search(self,title,year):
        resp_json= await self._search(title)
        search_data_list = await self.parse_search(resp_json)

        search_result=SearchResult(title,[])

        if len(search_data_list)==0:
            return search_result
        target_data=self.select_data(search_data_list,title,year)
        resp_json=await self.get_detail(target_data['idcode'])
        detail_data=await self.parse_detail(resp_json)
        detail_1080p_list=detail_data['ecca']['WEB-1080P']
        detail_4k=detail_data['ecca']['WEB-4K']
        resource_1080p_list=self.to_resource(detail_1080p_list)
        resource_4k=self.to_resource(detail_4k)

        filter_resource_list= self.filter(resource_4k,resource_1080p_list)
        search_result=SearchResult(keyword=title,result=filter_resource_list)
        return search_result
    def to_resource(self,detail_list):

        resource_list=[]
        for detail in detail_list:
            url = self.base_url + detail['down']
            title_ = detail['zname']
            format_name = BuTaiLinEpisodeNamer.generate_name([title_])[0]
            resource = Services.crawler_torrent.crawler.Resource(url=url, format_name=format_name.format_name,
                                                                 title=title_, type=ResourceType.TORRENT)
            resource_list.append(resource)
        return resource_list

    def filter(self,resource_4k_list,resource_1080p_list):
        """
        尽量选择4k资源，如果不存在则在1080p中寻找，同时筛选集合之间重叠最少的部分
        :param resource_4k_list:
        :param resource_1080p_list:
        :return:
        """
        format_name_4k_collection=[
            i.format_name for i in resource_4k_list
        ]
        format_name_1080p_collection=[
            i.format_name for i in resource_1080p_list
        ]
        resource_4k_maps={
            i.format_name:i
            for i in resource_4k_list
        }
        resource_1080p_maps={
            i.format_name:i
            for i in resource_1080p_list
        }
        not_exist_num_list= BuTaiLinEpisodeNamer.is_collection_episode_in_other_collection(format_name_4k_collection,format_name_1080p_collection)
        fill_4k_by_1080p=BuTaiLinEpisodeNamer.find_collection_episode_by_list_num(not_exist_num_list,format_name_4k_collection)
        deduplicate_4k_collection=BuTaiLinEpisodeNamer.remove_duplicates(format_name_4k_collection)

        fileter_resource=[
            resource_4k_maps[i]
            for i in deduplicate_4k_collection
        ]
        fill_4k_by_1080p_resource=[
            resource_1080p_maps[i]
            for i in fill_4k_by_1080p
        ]
        fileter_resource.extend(fill_4k_by_1080p_resource)
        return fileter_resource
    async def close(self):
        await self.session.close()


async def main():

    crawler=BuTaiLinCrawler()
    result= await crawler.search('折腰')
    print(result)
if __name__ == '__main__':
    asyncio.run(main())