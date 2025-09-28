from http.cookies import SimpleCookie

import aiohttp


def make_cookiejar(cookies_str: str) -> aiohttp.CookieJar:
    cookie = SimpleCookie()
    cookie.load(cookies_str)
    cookies_dict = {key: morsel.value for key, morsel in cookie.items()}
    jar = aiohttp.CookieJar()
    jar.update_cookies(cookies_dict)
    return jar