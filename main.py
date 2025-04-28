import asyncio
import json
from logging import Logger

from agents import Runner, function_tool, Agent
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from rich.console import Console

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import settings
from CrawlerResource.crawler_douban import CrawlerDouban
from QuarkDisk import QuarkDisk, ParseQuarkShareLInk
from database import engine
from models.resource import Resource, ResourceCategory
import logging
import os

from pansearch.providers import AipansouProvider

def setup_logger(log_file: str = "app.log"):
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = os.path.dirname(log_file)
    if log_dir:  # 只有log_dir不是空字符串才创建目录
        os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


share_context:ParseQuarkShareLInk|None=None
default_quark_disk:QuarkDisk = None
update_path:str=None
share_episode_list=None

latest_file_name_struct_response=None
logger=setup_logger()
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
def save_to_disk():
    pass
class EpisodeStruct(BaseModel):
    # fid: str
    file_name: str
    # share_fid_token: str
@function_tool()
async def ls_dir_share(share_link:str,max_deep:int=1):
    """
    返回目录树
    :param max_deep:默认为1,遍历深度，为0时只处理父目录文件信息，1时遍历1级子目录文件信息，以此类推。
    :param     share_link:别人分享的链接

    :return:返回目录树
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
            if len(file_detail_list)==0:
                return '该目录为空'
            result_detail_list = [{
                'fid':file_detail['fid'],
                'file_name': file_detail['file_name'],
                'file_type': file_detail['file_type'],
                 'absolute_path': f'{p_dir_path}/{file_detail['file_name']}',
                 'pdir_fid': file_detail['pdir_fid'],
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
        global share_episode_list
        share_episode_list=result_detail_list
        from rich.tree import Tree

        tree=Tree('/')
        def _traverse_add_tree(l,t):
            if isinstance(l,str):
                t.add(l)
            else:
                for i in l:
                    t1= t.add(i['file_name'])
                    if i['file_type'] == 0:
                        _traverse_add_tree(i['child'],t1)
        _traverse_add_tree(result_detail_list,tree)
        # 打印树（但其实是录制下来）
        console=Console(record=True)
        console.print(tree)
        # 把录制的内容取出来
        tree_str = console.export_text()
        # print(json.dumps(result_detail_list, ensure_ascii=False,indent=2))
        return tree_str
    except Exception as e:
        print(e)
        return e
async def _update_disk(need_update_list:[]):
    """
    添加剧集信息持久化存储
    :param latest_episode_info: 最新剧集的信息
    :param episode_info_list:  被添加的剧集信息list,必须仔细斟酌确保完整，否则会出错
    :return:
    """

    global share_context
    pwd_id=share_context.pwd_id
    stoken=share_context.stoken
    global default_quark_disk
    global update_path
    to_pdir_fid=(await default_quark_disk.get_fids([update_path]))[0]['fid']
    fid_list=[i['fid'] for i in need_update_list]
    fid_token_list=[i['share_fid_token'] for i in need_update_list]
    print(pwd_id,stoken,to_pdir_fid,fid_list,fid_token_list)
    try:
        issucces= await default_quark_disk.save_file(fid_list,fid_token_list,to_pdir_fid,pwd_id,stoken)
        if issucces:
            logger.info(f'✅转存成功，目录：{update_path}\n内容：{json.dumps(need_update_list,ensure_ascii=False,indent=2)}')
    except Exception as e:
        logger.error(e)
    return True
@function_tool()
async def print_result(updated_file:EpisodeStruct,match_updated_file:EpisodeStruct,episode_info:str,desc_sort_episode_info_list:list[EpisodeStruct]):
    """
     打印处理的结果
     :param episode_info: 剧集元数据
     :param match_updated_file: 与updated_file_name对于元数据信息匹配的文件
     :param updated_file: 影视库已经更新的文件
     :param desc_sort_episode_info_list: 按照剧集名降序排序的剧集信息list,越新的剧集越靠前
     :return:
     """
    need_list = []
    logger.info(f'需要更新的开始的文件名：{updated_file.file_name}    匹配的文件名为{match_updated_file.file_name}   剧集元信息：{episode_info}'  )
    file_name_list = [i.file_name for i in desc_sort_episode_info_list]
    if match_updated_file.file_name in file_name_list:

        for i in desc_sort_episode_info_list:
            if i.file_name != match_updated_file.file_name:
                need_list.append(i.model_dump())
            else:
                break
        global share_episode_list
        map_={}
        async def _traverse_(t):
            if isinstance(t,str):
                return
            for i in t:
                map_.update({
                    i['file_name']:i
                })
                if i.get('child'):
                    await  _traverse_(i['child'])
        await _traverse_(share_episode_list)

        need_detail_list=[]
        for i in need_list:
            if map_.get(i['file_name']):
                need_detail_list.append(map_[i['file_name']])
        # print(json.dumps(need_detail_list, ensure_ascii=False, indent=2))
        await _update_disk(need_detail_list)
        return json.dumps(need_list)
    else:
        logger.warning('无可更新的文件')
    return True


@function_tool()
async def print_result_1(latest_file_name:str):
    """
    打印处理的结果
    :param latest_file_name: 剧集为最新的文件名
    :return:
    """
    global latest_file_name_struct_response
    latest_file_name_struct_response=latest_file_name
    return True

def get_ai_agent(ins:str,tools:[]):
    return Agent(
        name="Assistant",
        instructions=ins,
        model=LitellmModel(
            model=f'openai/{settings.Current_AI['model']}',
            api_key=settings.Current_AI['key'],
            base_url=settings.Current_AI['url'],
        ),
        tools=tools,
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
    global update_path
    update_path=settings.STORAGE_BASE_PATH


    # agent=get_ai_agent('我将提供三个关键参数1.文件名：{updated_file_name}，代表我的媒体库已更新到的影视文件名 2.{link}用于同步我的影视库的外部资源链接 3.{title}代表当前被更新的影视名称。收到参数后，无需与我交互，请独立确保完成以下所有步骤 ：1.自主分析{updated_file_name}并得到剧集元数据 2.解析资源链接得到目录树 3.当目录树中存在不同季度的影视时,只寻找与{title}模糊匹配相似度最高的目录 4.在相关的目录中分析文件名并得到剧集元数据，如果解析得到的当前目录的所有文件名提取的剧集元数据都不匹配{updated_file_name}的剧集元数据，自主增加max_deep回到执行步骤2  5.自主完成分析根据剧集元数据的最新度对文件list降序排序 6.自主完成分析所有文件中,剧集元数据与{updated_file_name}的剧集元数据相匹配的文件名，这将作为增量更新的重要参数 7.存储增量更新的剧集信息 ')
    agent=get_ai_agent('我将提供三个关键参数1.文件名：{updated_file_name}，代表我的媒体库已更新到的影视文件名 2.{link}用于同步我的影视库的外部资源链接 3.{title}代表当前被更新的影视名称。收到参数后，无需与我交互，请独立确保完成以下所有步骤 ：1.解析资源链接得到目录树 2.当目录树中存在不同季度的影视时,只寻找与{title}模糊匹配相似度最高的目录,并分析出此目录的绝对路径 3.只关注后缀名为.mp4 .mkv的文件 4.目录中的文件命名方式与{updated_file_name}可能有很大差别，甚至文件格式的也不同，这不要紧，因为文件名中必然隐含着关于剧集信息的元数据，请在目录中寻找与{updated_file_name}关于剧集元数据相似的文件，例如：“S01E24.2160p.mp4”与“24.mkv”都包含了剧集元数据：“24”，因此它两匹配，如果没找到就自主增加max_deep回到执行步骤1  5.自主完成分析根据剧集元数据的最新度对文件list降序排序  6.打印处理的结果',
                       tools=[ls_dir_share,print_result])
    result = await  Runner.run(agent, input='{updated_file_name}="0412.mp4" {link}="https://pan.quark.cn/s/6d687312b70a" {title}="哈哈哈哈哈")')
    print(result.final_output)
    print(result)
async def _get_latest_file_name(share_link:str):
    agent=  get_ai_agent('我将提供此参数：1.{share_link}代表资源链接 2.{title}代表影视资源title。收到参数后，无需与我交互，请独立确保完成以下所有步骤 ：1.解析资源链接得到目录树 2.当目录树中存在不同季度的影视时,只寻找与{title}模糊匹配相似度最高的目录,或者当不存在季度名的目录时，请自主分析哪些目录是匹配的并决定关注此目录  3.只关注后缀名为.mp4 .mkv的文件  4.文件名中必然隐含着关于剧集信息的元数据,如果没找到就自主增加max_deep回到执行步骤1  5.自主完成分析得到最新剧集的文件名  6.打印处理的结果',
                         tools=[print_result_1,ls_dir_share],)
    result=    await  Runner.run(agent, input=share_link)
    global latest_file_name_struct_response
    if latest_file_name_struct_response is None:
        raise Exception(f'llm大模型未完成获取最新剧集文件名的任务：{result.final_output}')
    result=str(latest_file_name_struct_response)
    latest_file_name_struct_response=None
    return result

async def init_storage():
    with Session(engine) as session:
        statement=select(Resource).where(Resource.category == ResourceCategory.HOT_CN_DRAMA)
        results=session.exec(statement)
        resources=results.all()
        for r in resources:
            if r.updated_episodes is None or r.updated_episodes =='':
                aipansou_provider=AipansouProvider()
                title=r.title
                result=  aipansou_provider.search(title)[0]
                share_link=result.url
                try:
                    latest_episode_info = await _get_latest_file_name(
                       f'{{share_link}}="{share_link}" {{title}}="{title}"')
                    logger.info(f'✅{share_link}  |  {title}，获取最新剧集文件名：{latest_episode_info}')
                except Exception as e:
                    logger.error(f'❌{share_link}  |  {title}，获取最新剧集文件名出错：{e}')
                    continue

                share_context1=await QuarkDisk.parse_share_url(share_link)
                pdir_fid='0'
                while True:
                    ls_list=(await share_context1.ls_dir(pdir_fid))['list']
                    if len(ls_list) == 1 and ls_list[0]['file_type'] ==0:
                        pdir_fid=ls_list[0]['fid']
                    else:
                        pwd_id=share_context1.pwd_id
                        stoken=share_context1.stoken
                        fid_list=[i['fid'] for i in ls_list]
                        share_fid_token_list=[i['share_fid_token'] for i in ls_list]
                        global default_quark_disk
                        to_pdir_path=r.storage_path
                        try:
                           await  default_quark_disk.mkdir(to_pdir_path)
                           logger.info(f"创建{to_pdir_path}成功")
                        except Exception as e:
                            logger.error(e)
                        to_pdir_fid=(await default_quark_disk.get_fids([to_pdir_path]))[0]['fid']
                        try:
                            if await  default_quark_disk.save_file(fid_list=fid_list,fid_token_list=share_fid_token_list,to_pdir_fid=to_pdir_fid,stoken=stoken,pwd_id=pwd_id):
                                logger.info(f'✅转存到{to_pdir_path}成功')
                                r.updated_episodes = latest_episode_info
                                session.add(r)
                                session.commit()
                        except Exception as e:
                            logger.error(e)
                        break

                await share_context1.close()
@dataclass
class WeatherReport:
    city: str
    temperature: float
    condition: str
async def test4():
    agent = Agent(
        name="WeatherReporter",
        instructions="你擅长将关于天气信息的模型序列化输出",
        output_type=WeatherReport,
        model=LitellmModel(
            model=f'openai/{settings.Current_AI['model']}',
            api_key=settings.Current_AI['key'],
            base_url=settings.Current_AI['url'],
        ),
    )
    result=    await  Runner.run(agent,'南京天气10度')
    print(result.final_output)


async def main():
    await _init()
    # await test1()
    await init_storage()

    await _del()
    print('结束')
asyncio.run(main())