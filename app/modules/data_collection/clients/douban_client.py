import asyncio
import atexit
import logging
from typing import Optional

import aiohttp

from app.database.models import MovieCategory,  MovieType
from app.modules.data_collection.schemas.douban_schemas import DoubanTVResponse, DoubanDetailResponse

logger = logging.getLogger()


class DoubanClient:
    def __init__(self):
        self.session = None
        self.base_url = 'https://frodo.douban.com'
        self.headers = {
            'user-agent': 'Rexxar-Core/0.1.3 api-client/1 com.douban.frodo/7.98.0(318) Android/28 product/M391Q vendor/MEIZU model/M391Q brand/MEIZU  rom/flyme4  network/wifi  udid/342316168c4c576021f1836339d6dd47a78a45b9  platform/mobile com.douban.frodo/7.98.0(318) Rexxar/1.2.151  platform/mobile 1.2.151'
        }
        self._initialized = False
        self.secret_key='bf7dddc7c9cfe6f7'

    async def init(self):
        """创建aiohttp会话"""
        if not self._initialized:
            connector = aiohttp.TCPConnector(ssl=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            self._initialized = True

    async def shutdown(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self._initialized = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    async def _fetch_hot_raw_data(self, tv_type:  MovieCategory, count: int):
        url = ''
        params = {}
        if tv_type == MovieCategory.CHINA:
            params = {
                'playable': '0',
                'start': '0',
                'count': count,
                'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                'rom': 'flyme4',
                'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                's': 'rexxar_new',
                'channel': 'Baidu_Market',
                'timezone': 'Asia/Shanghai',
                'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                'os_rom': 'flyme4',
                'sugar': '0',
                'loc_id': '108288',
                '_sig': '+USKTbukOV+f5oTj1EKy4US1aFw=',
                '_ts': '1745652498'
            }
            url = '/api/v2/subject_collection/tv_domestic/items'
        elif tv_type == MovieCategory.EUROPE:
            params = {
                'playable': '0',
                'start': '0',
                'count': count,
                'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                'rom': 'flyme4',
                'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                's': 'rexxar_new',
                'channel': 'Baidu_Market',
                'timezone': 'Asia/Shanghai',
                'device_id': '342316168c4c576021f183636d9d47a78a45b9',
                'os_rom': 'flyme4',
                'sugar': '0',
                'loc_id': '108288',
                '_sig': 'AW5I71bx9kiabl4FMhQlZTFRTso=',
                '_ts': '1745598097'
            }
            url = '/api/v2/subject_collection/tv_american/items'
        elif tv_type == MovieCategory.KOREA:
            params = {
                'playable': '0',
                'start': '0',
                'count': count,
                'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                'rom': 'flyme4',
                'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                's': 'rexxar_new',
                'channel': 'Baidu_Market',
                'timezone': 'Asia/Shanghai',
                'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                'os_rom': 'flyme4',
                'sugar': '0',
                'loc_id': '108288',
                '_sig': 'tTTyNDRR1aeYgpgA2qs9Po7HAww=',
                '_ts': '1745598444'
            }
            url = '/api/v2/subject_collection/tv_korean/items'
        elif tv_type == MovieCategory.JAPAN:
            params = {
                'playable': '0',
                'start': '0',
                'count': count,
                'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                'rom': 'flyme4',
                'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                's': 'rexxar_new',
                'channel': 'Baidu_Market',
                'timezone': 'Asia/Shanghai',
                'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                'os_rom': 'flyme4',
                'sugar': '0',
                'loc_id': '108288',
                '_sig': 'j414HcvEIiBKkWsRPDHMThwQWzY=',
                '_ts': '1745598415'
            }
            url = '/api/v2/subject_collection/tv_japanese/items'
        elif tv_type == MovieCategory.ANIMATION:
            params = {
                'playable': '0',
                'start': '0',
                'count': count,
                'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                'rom': 'flyme4',
                'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                's': 'rexxar_new',
                'channel': 'Baidu_Market',
                'timezone': 'Asia/Shanghai',
                'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                'os_rom': 'flyme4',
                'sugar': '0',
                'loc_id': '108288',
                '_sig': 'oVn32qX5K7PeOFN5M4e3TfJutvQ=',
                '_ts': '1745598494'
            }
            url = '/api/v2/subject_collection/tv_animation/items'
        else:
            return None

        async with self.session.request(url=self.base_url + url, params=params, method='GET') as resp:
            try:
                resp_json = await resp.json()
                return resp_json
            except Exception as e:
                logger.error(f"爬取数据失败: {e}")
                return None

    async def get_hot_tv(self, tv_type:  MovieCategory  , count: int) -> Optional[DoubanTVResponse]:
        """获取热门电视剧数据（包含结构化解析）"""
        raw_data = await self._fetch_hot_raw_data(tv_type, count)
        if not raw_data:
            return None

        return DoubanTVResponse(**raw_data)

    async def search(self,key:str):
        url=f"{self.base_url}/api/v2/search/subjects"
        headers = {
            'Host': 'frodo.douban.com',
            'user-agent': 'api-client/1 com.douban.frodo/7.98.0(318) Android/28 product/M391Q vendor/MEIZU model/M391Q brand/MEIZU  rom/flyme4  network/wifi  udid/342316168c4c576021f1836339d6dd47a78a45b9  platform/mobile',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Cookie': 'bid=XNEw1YnsIl0'
        }
        sig,ts,_=self.generate_sig_exact(url=url,method='GET',token=None,secret_key=self.secret_key,timestamp=None)
        params = {
            'q':key,
            'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
            'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
            'channel': 'Baidu_Market',
            'timezone': 'Asia/Shanghai',
            'os_rom': 'flyme4',
            '_sig': sig,
            '_ts': ts
        }
        async with self.session.request(url=url , params=params, method='GET',headers=headers) as resp:
            try:
                resp_json = await resp.json()
                return resp_json
            except Exception as e:
                logger.error(f"爬取数据失败: {e}")
                return None

    async def detail(self,douban_id:str,movie_type:MovieType):
        if movie_type == MovieType.TV:

            url=f'{self.base_url}/api/v2/tv/{douban_id}'
        else:
            url=f'{self.base_url}/api/v2/movie/{douban_id}'
        headers = {
            'Host': 'frodo.douban.com',
            'user-agent': 'api-client/1 com.douban.frodo/7.98.0(318) Android/28 product/M391Q vendor/MEIZU model/M391Q brand/MEIZU  rom/flyme4  network/wifi  udid/342316168c4c576021f1836339d6dd47a78a45b9  platform/mobile',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Cookie': 'bid=XNEw1YnsIl0'
        }
        sig, ts, _ = self.generate_sig_exact(url=url, method='GET', token=None, secret_key=self.secret_key,
                                             timestamp=None)
        params = {
            'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
            'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
            'channel': 'Baidu_Market',
            'timezone': 'Asia/Shanghai',
            'os_rom': 'flyme4',
            '_sig': sig,
            '_ts': ts
        }
        async with self.session.request(url=url, params=params, method='GET',headers=headers) as resp:
            try:
                resp_json = await resp.json()
                print(resp_json)
                return DoubanDetailResponse(**resp_json)
            except Exception as e:
                logger.error(f"爬取数据失败: {e}",exc_info=True)
                return None


    @staticmethod
    def generate_sig_exact(url: str, method: str, token: str, secret_key: str, timestamp: int = None):
        """
        精确复现 Java C0099d.m197T 的签名算法
        - path: HttpUrl.parse(url).encodedPath() -> Uri.decode(...) -> (remove trailing '/') -> Uri.encode(...)
          等价于 urllib.parse.unquote(path) 然后 urllib.parse.quote(..., safe='')
        - 拼接: METHOD + "&" + ENCODED_PATH [+ "&" + token] + "&" + TIMESTAMP
        - HMAC-SHA1(secret_key, string_to_sign), Base64 NO_WRAP
        """
        # 解析 path 并 decode
        import time
        import hmac
        import hashlib
        import base64
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)  # Uri.decode(encodedPath) 等价
        # 去掉末尾斜杠（Java: if (decode.endsWith("/")) decode = substring(...))
        if path.endswith("/"):
            path = path[:-1]
        # 再 encode，必须把 '/' 也编码 -> safe=''，这与 Android Uri.encode 行为一致
        encoded_path = urllib.parse.quote(path, safe='')

        # 时间戳（秒）
        if timestamp is None:
            timestamp = int(time.time())
        # 构造待签名字符串
        s = f"{method}&{encoded_path}"
        if token:
            s += f"&{token}"
        s += f"&{timestamp}"

        # HMAC-SHA1 + Base64 (no newline)
        mac = hmac.new(secret_key.encode('utf-8'), s.encode('utf-8'), hashlib.sha1).digest()
        sig = base64.b64encode(mac).decode('utf-8')  # Python 的 b64encode 默认不换行 -> 等同于 Android NO_WRAP

        return sig, str(timestamp), s




# ==================== 单例实现部分 ====================

# 模块级单例实例



_douban_client_instance:Optional[DoubanClient] = None

async def get_douban_client() -> DoubanClient:
    """获取豆瓣爬虫单例实例"""
    global _douban_client_instance
    if _douban_client_instance is None:
        _douban_client_instance = DoubanClient()
        await _douban_client_instance.init()
    return _douban_client_instance

@atexit.register
def close_session():
    try:
        asyncio.run(shutdown_douban_client())
    except RuntimeError:
        # 如果已经在事件循环里，可以忽略
        pass

async def shutdown_douban_client():
    """关闭豆瓣爬虫实例"""
    global _douban_client_instance
    if _douban_client_instance is not None:
        await _douban_client_instance.shutdown()
        _douban_client_instance = None
# 使用示例
async def main():
    # 获取单例实例
    crawler = await get_douban_client()
    # 使用爬虫
    result = await crawler.search('凡人修仙传')
    print(result)
    re=await crawler.detail(result['subjects']['items'][0]['target_id'],MovieType.TV)
    print(re)

    # 程序结束时清理资源
    await shutdown_douban_client()

    # url = "https://frodo.douban.com/api/v2/movie/36221247"
    # method = "GET"
    # token = None  # Java 把 null 视为空，不会插入
    # secret_key = "bf7dddc7c9cfe6f7"  # 你在 SecretKeySpec hook 中看到的字符串
    # timestamp = None  # Java 日志里给出的时间戳
    #
    # sig, ts, string_to_sign = DoubanClient.generate_sig_exact(url, method, token, secret_key, timestamp)
    # print("string_to_sign =", string_to_sign)
    # print("_sig =", sig)
    # print("timestamp =", ts)
if __name__ == '__main__':
    asyncio.run(main())