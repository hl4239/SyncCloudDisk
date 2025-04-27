import asyncio
import json

from agents import Runner, function_tool, Agent
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import settings
from CrawlerResource.crawler_douban import CrawlerDouban
from QuarkDisk import QuarkDisk, ParseQuarkShareLInk
from database import engine
from models.resource import Resource, ResourceCategory

share_context:ParseQuarkShareLInk|None=None
default_quark_disk:QuarkDisk = None

share_episode_dict=None

async def _init():
    global default_quark_disk
    default_quark_disk = QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    await default_quark_disk.connect()
async def _del():
    global default_quark_disk
    global share_context
    await default_quark_disk.close()
    if share_context is not None:
        await share_context.close()
async def _crawler_resource(tv_type:ResourceCategory):
    base_path=settings.STORAGE_BASE_PATH
    resources=[]
    async with  CrawlerDouban() as crawler:
        resp_json=await crawler.get_hot_tv(tv_type)
        print(resp_json)
        try:
            sub_items=resp_json['subject_collection_items']
            for item in sub_items:
                title=f'{item["title"]}({item['year']})'
                subtitle=item["card_subtitle"]
                description=item['comment']
                pic_path=item['pic']['large']
                storage_path=f'{base_path}/{tv_type.value}/{title}'
                total_episode=item['episodes_info']

                resource=Resource(title=title, subtitle=subtitle, description=description,image_path=pic_path,category=tv_type,storage_path=storage_path,total_episodes=total_episode)
                resources.append(resource)
            return resources
        except Exception as e :
            print(e)
            return  None
async def update_to_datebase(update_list:[Resource|None]):
    check_title = [i.title for i in update_list]
    with Session(engine) as session:
        statement = select(Resource).where(Resource.title.in_(check_title))
        exsiting_resources = session.exec(statement).all()
        existing_resources_map: dict[str, Resource] = {
            resource.title:resource  for resource in exsiting_resources
        }
        mapper=inspect(Resource).mapper
        resources_to_add=[]
        resources_to_update=[]
        for resource in update_list:
            exist_resource=existing_resources_map.get(resource.title)
            if exist_resource:
                for column in mapper.columns:
                    if column.primary_key:
                        continue
                    field_name=column.key
                    if hasattr(exist_resource, field_name):
                        new_value=getattr(resource, field_name)
                        setattr(exist_resource, field_name, new_value)
                session.add(exist_resource)
                resources_to_update.append(exist_resource.title)
            else :
                session.add(resource)
                resources_to_add.append(resource.title)
        try:
            # 提交事务
            session.commit()
            print(f"操作完成。插入 {len(resources_to_add)} 条记录, 更新 {len(resources_to_update)} 条记录。")
            if resources_to_add:
                print(f"插入的标题: {resources_to_add}")
            if resources_to_update:
                print(f"更新的标题: {resources_to_update}")

        except IntegrityError as e:
            session.rollback()
            print(f"发生数据库完整性错误 (例如，标题重复): {e}")
            # 可以进一步处理 e 来获取更具体的错误信息
            # 例如，对于 SQLite，可以通过 e.orig 获取 sqlite3.IntegrityError 实例
            # 如果是其他数据库，需要查看相应的驱动文档
        except Exception as e:
            session.rollback()
            print(f"处理资源时发生未知错误: {e}")
            raise  # 重新抛出，或者根据需要处理
async def update_resource():
    update_list=[]
    for tv_type in ResourceCategory:
        update_resources=   await _crawler_resource(tv_type)
        if update_resources is None:
            print(f'抓取{tv_type}失败')
            continue
        update_list.extend(update_resources)
    await update_to_datebase(update_list)






@function_tool
def get_weather(city: str):
    """
    查询天气
    :param city: 要查寻得城市名
    :return:
    """
    return '11度'

def save_to_disk():
    pass

class EpisodeStruct(BaseModel):
    fid: str
    file_name: str
    share_fid_token: str

@function_tool()
async def ls_dir_share(share_link:str,max_deep:int=1):
    """
    基于别人分享链接的文件浏览，指定父目录id列出所有文件信息


    file_type: 0 indicates a folder, 1 indicates a file
    :param max_deep:默认为1,遍历深度，为0时只处理父目录文件信息，1时遍历1级子目录文件信息，以此类推。
    :param     share_link:别人分享的链接

    :return:返回父目录的所有文件信息
    """
    global share_context
    try:

        if not hasattr(share_context, 'share_link'):
            share_context=await QuarkDisk.parse_share_url(share_link)
        elif share_context.share_link!=share_link:
            await share_context.close()
            share_context = await QuarkDisk.parse_share_url(share_link)

        async def _traverse_dir_share(current_deep: int, max_deep: int, fid='0', p_dir_path='', ):
            if (current_deep > max_deep):
                return f"请增加max_deep以查看此目录,current_deep={current_deep},max_deep={max_deep}"
            global share_context
            print(fid)
            file_detail_list = (await share_context.ls_dir(fid))['list']

            result_detail_list = [{
                'fid':file_detail['fid'],
                'file_name': file_detail['file_name'],
                'file_type': file_detail['file_type'],
                 # 'absolute_path': f'{p_dir_path}/{file_detail['file_name']}',
                 # 'pdir_fid': file_detail['pdir_fid'],
                 'share_fid_token':file_detail['share_fid_token'],
            }
                for file_detail in file_detail_list]
            for result_detail in result_detail_list:
                if result_detail['file_type'] == 0:
                    result_detail.update({
                        'child': await _traverse_dir_share(current_deep + 1, max_deep, result_detail['fid'],
                                                           f'{p_dir_path}/{result_detail['file_name']}')
                    })

            return result_detail_list
        result_detail_list=await _traverse_dir_share(current_deep=0,max_deep=max_deep,fid='0',p_dir_path='')
        global share_episode_dict
        share_episode_dict=result_detail_list



        print(json.dumps(result_detail_list, ensure_ascii=False,indent=2))
        return json.dumps(result_detail_list)
    except Exception as e:
        print(e)
        return e

async def save_episode_info(episode_info_list:list[EpisodeStruct],latest_episode_info:EpisodeStruct):
    """
    添加剧集信息持久化存储
    :param latest_episode_info: 最新剧集的信息
    :param episode_info_list:  被添加的剧集信息list,必须仔细斟酌确保完整，否则会出错
    :return:
    """
    result= [i.model_dump() for i in episode_info_list]
    print(json.dumps(result, ensure_ascii=False,indent=2))
    print(f'最新剧集信息：{json.dumps(latest_episode_info.model_dump(),ensure_ascii=False,indent=2) }')
    # global share_context
    # pwd_id=share_context.pwd_id
    # stoken=share_context.stoken
    # global default_quark_disk
    # to_pdir_fid=(await default_quark_disk.get_fids([settings.STORAGE_BASE_PATH]))[0]['fid']
    # fid_list=[i.fid for i in episode_info_list]
    # fid_token_list=[i.share_fid_token for i in episode_info_list]
    # print(pwd_id,stoken,to_pdir_fid,fid_list,fid_token_list)
    # await default_quark_disk.save_file(fid_list,fid_token_list,to_pdir_fid,pwd_id,stoken)

    return True
@function_tool()
async def save_need_update_episode_info(updated_episode_info:EpisodeStruct,desc_sort_episode_info_list:list[EpisodeStruct]):
   """
    保存需要更新的剧集信息
    :param desc_sort_episode_info_list: 按照剧集名降序排序的剧集信息list,越新的剧集越靠前
    :param updated_episode_info: 已更新到的剧集信息，
    :return:
    """
   need_list=[]
   for i in desc_sort_episode_info_list:
       if i.file_name!=updated_episode_info.file_name:
           need_list.append(i.model_dump())
       else: break
   print(json.dumps(need_list, ensure_ascii=False,indent=2))
   return json.dumps(need_list)

def get_ai_agent(ins:str):
    return Agent(
        name="Assistant",
        instructions=ins,
        model=LitellmModel(
            model=f'openai/{settings.Current_AI['model']}',
            api_key=settings.Current_AI['key'],
            base_url=settings.Current_AI['url'],
        ),
        tools=[get_weather,ls_dir_share,save_need_update_episode_info],
    )

async def test2():
    list = [Resource(
        title="鬼灭之刃",
        category=ResourceCategory.HOT_ANIME,
        storage_path="/mnt/share/anime/鬼灭之刃dsdasdsadasadss",
        total_episodes=55,  # 假设总集数
        updated_episodes=20,
        tags=["热血", "奇幻", "战斗"])]
    await    update_to_datebase(list)

async def test3():
    await update_resource()




async def test1():
    global default_quark_disk

    agent=get_ai_agent('我将提供两个关键参数1.{updated_episode},代表我的影视库以及更新到第{updated_episode} 2.{link}用于同步我的影视库的外部资源链接。收到这两个参数后，无需与我交互，请独立确保完成以下所有步骤 ：1.解析资源链接的文件信息 2.如果第{updated_episode}剧集信息对应的文件不存在，自主增加max_deep 3.自主完成分析根据剧集的最新度降序排序 4.自主完成分析并得到第{updated_episode}集对应的剧集信息 5.存储需要更新的剧集信息 ')
    result = await  Runner.run(agent, input='{updated_episode}=20 {link}=https://pan.quark.cn/s/8a4d9ed0c8b6')
    print(result.final_output)
    print(result)




async def main():
    await _init()
    await test1()
    await _del()
    print('结束')

asyncio.run(main())