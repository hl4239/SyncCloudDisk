import asyncio
import json
import uuid
from itertools import groupby
from pathlib import Path

from playwright.async_api import Playwright, async_playwright
from playwright.sync_api import BrowserType
from sqlmodel import Session, select

from database import engine
from models.resource import Resource

links = [

# 'https://pan.quark.cn/s/2c73428ee0f3,https://pan.quark.cn/s/576c15af008e,https://pan.quark.cn/s/233af153c79c,https://pan.quark.cn/s/42495cd3c7fe,https://pan.quark.cn/s/ad7cda603cfc,https://pan.quark.cn/s/d5abf209527f,https://pan.quark.cn/s/a3d512330d5d,https://pan.quark.cn/s/d74de71cafa7,https://pan.quark.cn/s/6fbc22ef8383,https://pan.quark.cn/s/bd9fb1ed2616,https://pan.quark.cn/s/3dc55dac5424,https://pan.quark.cn/s/7f686dc2dad5',
#
# 'https://pan.quark.cn/s/1900be187215,https://pan.quark.cn/s/294640b052ac,https://pan.quark.cn/s/f7ae168d3d23,https://pan.quark.cn/s/901ae47c74df,https://pan.quark.cn/s/585f6f20766b,https://pan.quark.cn/s/52e8a0b34835,https://pan.quark.cn/s/8db7f7c4851a,https://pan.quark.cn/s/eb097de9364e,https://pan.quark.cn/s/86ed9576ffad,https://pan.quark.cn/s/3868f569e317,https://pan.quark.cn/s/ff546a7a2d69'
# ,
#     'https://pan.quark.cn/s/42592af41cc5,https://pan.quark.cn/s/38eae2a7e4f9,https://pan.quark.cn/s/078365b4b6ef,https://pan.quark.cn/s/cc36813a8a89,https://pan.quark.cn/s/9fc14a190395,https://pan.quark.cn/s/a4d623257223,https://pan.quark.cn/s/d3da16dec273,https://pan.quark.cn/s/736dbe505cb1,https://pan.quark.cn/s/10bdb0bb3724,https://pan.quark.cn/s/8665389ede36,https://pan.quark.cn/s/8308a6c84126,https://pan.quark.cn/s/3d36d2038ac1,https://pan.quark.cn/s/0075f56981e0,https://pan.quark.cn/s/ff441cd3d96',
#
#     'https://pan.quark.cn/s/1c589aff15c3,https://pan.quark.cn/s/45bc99e3b956,https://pan.quark.cn/s/d320d58fe76f'
'https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj,https://aipanso.com/s/A4KsiSFpqbpNWO7AyNHgcknj'
]


def _generate_uuid():
    unique_id = uuid.uuid1()
    print(unique_id)
    return unique_id

async def _submit(browser,link:str):


    context = await browser.new_context(proxy={"server": f"socks5://127.0.0.1:8443"})
    # 当前文件的绝对路径
    current_file = Path(__file__).resolve()

    # 当前文件所在的目录
    js_path = current_file.parent.parent/'libs'/'stealth.min.js'
    # await context.add_init_script(path=r'D:\HLworkspace\temp\有盘搜脚本\libs\stealth.min.js')

    await context.add_init_script(path=js_path)
    page = await context.new_page()
    # 设置自定义请求头


    await page.set_extra_http_headers({
        "User-Agent": f"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/13{_generate_uuid()}.0.0.0 Mobile Safari/537.36",
    })


    # await page.goto('https://bot.sannysoft.com/')
    # await asyncio.sleep(1000)
    await page.goto('https://aipanso.com/submitRes')
    print(await page.title())

    try :

        await page.wait_for_selector("button.van-dialog__confirm",timeout=20000)
    except Exception as e :
        print(e)
        await context.close()

        raise

    await page.click("button.van-dialog__confirm")

    # 填入链接
    await page.fill('#link', link)
    try:
        # 点击提交按钮
        await page.wait_for_selector("button.van-button--info",timeout=10000)
    except Exception as e :
        print(e)
        await context.close()
        raise
    await page.click("button.van-button--info")
    # 使用 Future 来接收回调里的数据
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    # 监听特定路径的响应
    async def on_response(response):
        if "/submitRes" in response.url and response.status == 200:
            print(f"⬅️ [API] Response: {response.status} {response.url}")
            try:
                body = await response.text()
                future.set_result(body)
                print("📦 Body:", body[:200])
            except Exception as e:
                print(F'响应监听回调报错：{e}')
                pass

    page.on("response", on_response)


    result=None
    try:
        result = await asyncio.wait_for(future, timeout=30)  # 设置超时避免卡住
        json_result = json.loads(result)
        result=json_result
    except Exception as e:
        result = None
        await context.close()
        raise
    await context.close()
    return result
async def batch_submit(link_create_list:[]):
    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)
        async def task_(browser:BrowserType,list_:[]):
            print(f'正在分享{len(list_)}个资源')
            if len(list_) > 20:
                print('❌超过了20个')
                return

            result={
                'success': False,
                'name':list_[0]['name']
            }
            link_str=','.join([i['share_link'] for i in list_])
            for retry in range(5):
                try:
                    json_result=    await _submit(browser,link_str)
                    if json_result is not None:
                        success=json_result['success']
                        if success:
                          result['success']=success
                          break
                        print(f'提交出错：success:{success}  准备第{retry}重试:')
                except Exception as e:
                    print(f'提交出错:{e}  准备第{retry}重试')
            print(f'name:{result["name"]}      提交结果：{result["success"]}')

        # 先按 'name' 排序
        link_create_list.sort(key=lambda link: link['name'])
        tasks=[task_(browser, list(link_list)) for name,link_list in groupby(link_create_list,lambda link:link['name'])]
        results=await asyncio.gather(*tasks)

async def push():
    with Session(engine) as session:
        resources = session.exec(select(Resource).where()).all()
    share_link_list=[]
    for resource in resources:
        if resource.share_handle.get('share_list'):
            share_list=resource.share_handle.get('share_list')
            for share in share_list:
                if share.get('share_link'):
                    share_link_list.append({
                        'name':share['account'],
                        'share_link':share['share_link']
                    })
    await batch_submit(share_link_list)


if __name__ == '__main__':
    asyncio.run(push())
