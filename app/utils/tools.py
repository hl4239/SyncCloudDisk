import asyncio
from http.cookies import SimpleCookie

import aiohttp


from typing import Union, Dict

def make_cookiejar(cookies: Union[str, Dict[str, str]], response_url=None, quote_cookie=True) -> aiohttp.CookieJar:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    jar = aiohttp.CookieJar(quote_cookie=quote_cookie, loop=loop)
    if isinstance(cookies, str):
        parsed_cookies = {}
        for item in cookies.split(";"):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                parsed_cookies[k.strip()] = v.strip().strip('"')
        cookies_to_update = parsed_cookies
    elif isinstance(cookies, dict):
        cookies_to_update = cookies
    else:
        raise TypeError("cookies must be a string or a dictionary")

    if response_url:
        jar.update_cookies(cookies_to_update, response_url=response_url)
    else:
        jar.update_cookies(cookies_to_update)
    return jar