from Services.crawler_resource.crawler import QuarkFile, ResourceQuark, SearchResult
from Services.episode_namer_dir.public_episode_namer import PublicEpisodeNamer
from Services.quark_share_dir_tree import QuarkShareDirTree


class QuarkShareCrawler:
    def __init__(self):
        pass
    async def parse_quark_share(self, share_link: str):
        quark_dir_tree = QuarkShareDirTree.get_quark_share_tree(share_link)
        await quark_dir_tree.parse(10, refresh=True)
        video_list = quark_dir_tree.get_video_node_info()
        return video_list

    async def search(self,share_link:str,title:str):
        video_list = await self.parse_quark_share(share_link)
        resource_quark_list = [
            QuarkFile(file_name=i['file_name'], fid=i['fid'], share_fid_token=i['share_fid_token'])
            for i in video_list
        ]
        resource_quark_list = await self.clean_quark_file_list(resource_quark_list)

        resource_quark = ResourceQuark(title=title, url=share_link, file_list=resource_quark_list)
        search_result = SearchResult(keyword=title, result=[resource_quark])
        return search_result

    async def clean_quark_file_list(self, quark_file_list: [QuarkFile]):
        g_name_list = await PublicEpisodeNamer.generate_name([
            i.file_name
            for i in quark_file_list
        ])
        g_name_list = list({item.format_name: item for item in g_name_list}.values())

        remove_duplicate_list = PublicEpisodeNamer.remove_duplicates([
            i.format_name
            for i in g_name_list
        ])
        g_name_list = [
            i
            for i in g_name_list if i.format_name in remove_duplicate_list
        ]

        resource_quark_maps = {
            i.file_name: i
            for i in quark_file_list

        }
        for g in g_name_list:
            resource_quark_maps[g.original_name].format_name = g.format_name
        g_name_list = list({item.format_name: item for item in g_name_list}.values())

        remove_duplicate_list = PublicEpisodeNamer.remove_duplicates([
            i.format_name
            for i in g_name_list
        ])
        g_name_list = [
            i
            for i in g_name_list if i.format_name in remove_duplicate_list
        ]

        resource_quark_maps = {
            i.file_name: i
            for i in quark_file_list

        }
        for g in g_name_list:
            resource_quark_maps[g.original_name].format_name = g.format_name
        return [
            quark_file
            for quark_file in quark_file_list
            if quark_file.format_name is not None
        ]