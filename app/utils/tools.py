from http.cookies import SimpleCookie

import aiohttp


def make_cookiejar(cookies_str: str,response_url=None,quote_cookie=True) -> aiohttp.CookieJar:
    import aiohttp
    cookies = {}
    for item in cookies_str.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k.strip()] = v.strip().strip('"')
    jar = aiohttp.CookieJar(quote_cookie=quote_cookie)
    if response_url:

        jar.update_cookies(cookies, response_url=response_url)
    else:
        jar.update_cookies(cookies)
    return jar