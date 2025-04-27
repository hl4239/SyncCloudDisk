import asyncio
import json
import sys
import traceback
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

import ParseQuarkShareLInk

# 获取当前文件的父目录的父目录（即项目根目录）
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
import settings
from CloudDisk.QuarkDisk import QuarkDisk

quark_disk=None

# 创建 MCP 服务器实例
mcp = FastMCP("Demo Server")
share_context:ParseQuarkShareLInk=None

@mcp.tool()
async def ls_dir_share(share_link:str,fid:str,max_deep:int=999):
    """
    基于别人分享链接的文件浏览，指定父目录id列出所有文件信息
    默认按照文件名降序排序，因此如果在命名规范的前提下，剧集也会按降序排序，命名不规范就可能导致剧集是混乱的
    根目录的fid是0，因此你第一次查看此分享链接时应该会以fid为0调用
    file_type: 0 indicates a folder, 1 indicates a file
    :param max_deep:默认值为999，遍历深度，为0时只处理父目录文件信息，1时遍历1级子目录文件信息，以此类推。
    :param     share_link:别人分享的链接
    :param fid:父目录的id，根据此id访问父目录呃所有文件信息
    :return:返回父目录的所有文件信息
    """
    global share_context
    try:

        if not hasattr(share_context, 'share_link'):
            share_context=await QuarkDisk.parse_share_url(share_link)
        elif share_context.share_link!=share_link:
            await share_context.close()
            share_context = await QuarkDisk.parse_share_url(share_link)
        result_detail_list=await _traverse_dir_share(current_deep=0,max_deep=max_deep,fid=fid,p_dir_path='')
        print(json.dumps(result_detail_list, ensure_ascii=False,indent=2))
        return json.dumps(result_detail_list, ensure_ascii=False)
    except Exception as e:
        print(e)
        return e

async def _traverse_dir_share(current_deep:int,max_deep:int,fid='0',p_dir_path='',):
    if(current_deep>max_deep):
        return f"已达到遍历设定的最大深度,current_deep={current_deep},max_deep={max_deep}"
    global share_context
    print(fid)
    file_detail_list = (await share_context.ls_dir(fid))['list']

    result_detail_list = [{
        'fid': file_detail['fid'],
        'file_name': file_detail['file_name'],
        'file_type': file_detail['file_type'],
        'absolute_path':f'{p_dir_path}/{ file_detail['file_name']}',
        'pdir_fid': file_detail['pdir_fid'],

    }
        for file_detail in file_detail_list]
    for result_detail in result_detail_list:
        if result_detail['file_type']==0:
            result_detail.update({
                'child':await _traverse_dir_share(current_deep+1,max_deep,result_detail['fid'],f'{p_dir_path}/{result_detail['file_name']}')
            })
    return result_detail_list



@mcp.tool()
async def ls_dir_storage(path: str) :
    """
    基于我自己夸克账号的文件浏览，通过指定父目录路径列出所有文件信息

    Note:

    file_type: 0 indicates a folder, 1 indicates a file
    pdir_name: The parent directory path where the current file is located
    :param paths: The folder path to list
    :return: List of file/directory information
    """
    try:
        global quark_disk

        fids = await quark_disk.get_fids([path])

        file_detail_list = await quark_disk.ls_dir(fids[0]['fid'])
        result_detail=[{
            'file_name':file_detail['file_name'],
            'absolute_path':path+"/"+file_detail['file_name'],
            'file_type':file_detail['file_type'],
            'fid':file_detail['fid'],
            'pdir_name':path
        }
        for file_detail in file_detail_list]
        print(json.dumps(result_detail, ensure_ascii=False,indent=2))
        return json.dumps(result_detail, ensure_ascii=False)
    except Exception as e:
        print(str(e))
        return e

# @mcp.tool()
# def ls_dir_storage(path: str) -> list[dict[str, any]]:
#     try:
#         print(path)
#         return asyncio.run(_ls_dir_storage(path))
#     except Exception as e:
#         print(e)
@mcp.tool()
def get_weather(city:str):
    """
    根据城市名获得天气信息
    :param city: 城市名称
    :return:
    """
    return '18度'

async def main():
    global quark_disk
    quark_disk = QuarkDisk(config=settings.STORAGE_CONFIG['quark'][0])
    await quark_disk.connect()
    await ls_dir_share('https://pan.quark.cn/s/5dc390709ab4','0',max_deep=3)
    global mcp
    await mcp.run_stdio_async()


    # await _ls_dir_storage('/')
    # await ls_dir_storage('/-------------分享----------------/仙逆')
    # await quark_disk.close()
if __name__ == '__main__':

   asyncio.run(main())



