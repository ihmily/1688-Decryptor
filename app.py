import json
import re
import time
from typing import Dict, Any, Optional
import httpx
import execjs
from loguru import logger

"""
使用说明：
1.1688加密的接口几乎都是用的sign参数配合cookie进行鉴权
2.sign参数生成需要4个参数，分别是_m_h5_tk、毫秒时间戳、app_key、请求参数data数据
3.请求时带上生成的sign值和用来生成sign的时间戳即可
4.有部分接口没有用sign进行鉴权，使用的是_tb_token_参数，这个值可以通过接口获取并且在初始化的cookie中
"""

JS_VERSION = '2.7.0'
APP_KEY = '12574478'

headers = {
    'cookie': '',
    'referer': 'https://sycm.1688.com/ms/home/home?dateRange=2024-04-01%7C2024-04-30&dateType=month',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 '
                  'Safari/537.36 Edg/121.0.0.0',
}


def get_milliseconds_timestamp() -> int:
    return int(time.time() * 1000)


def jsonp_to_json(jsonp_data: str) -> Dict[str, Any] | None:
    try:
        match = re.match(r'.*?({.*}).*?', jsonp_data, re.S)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            raise ValueError('Invalid JSONP format')
    except (json.JSONDecodeError, re.error):
        raise ValueError('Invalid Input')


def cookies_str_to_dict(cookies_str: str) -> Dict[str, str]:
    cookies_dict = {}
    if cookies_str:
        cookies_list = cookies_str.split('; ')
        for cookie in cookies_list:
            key, value = cookie.split('=', 1)
            cookies_dict[key] = value
    return cookies_dict


def dict_to_cookies_str(cookies_dict: Dict[str, str]) -> str:
    cookie_str = '; '.join([f"{key}={value}" for key, value in cookies_dict.items()])
    return cookie_str


def update_cookie(cookie_list) -> Dict[str, str]:
    cookies_dict = cookies_str_to_dict(headers.get('cookie', {}))
    for cookie in cookie_list:
        cookies_dict[cookie['name']] = cookie['value']

    # 更新headers中的cookie
    new_cookie = dict_to_cookies_str(cookies_dict)
    headers['cookie'] = new_cookie
    return headers


def get_sign_params(_m_h5_tk: str, data: str) -> Dict[str, Any]:
    """
    生成API请求所需的签名参数。

    参数:
    _m_h5_tk (str): 存在cookie中，也可通过请求接口生成。
    data (str): 请求数据中的data参数值。
    """
    current_timestamp = get_milliseconds_timestamp()
    pre_sign_str = f'{_m_h5_tk.split("_")[0]}&{current_timestamp}&{APP_KEY}&' + data
    sign_js_path = './sign.js'
    sign = execjs.compile(open(sign_js_path).read()).call('sign', pre_sign_str)
    return {"sign": sign, "t": current_timestamp}


async def get_tb_token() -> None:
    params = {
        'group': 'tao',
        'target': 'https://work.1688.com/home/unReadMsgCount.htm?tbpm=1&callback=jQuery0',
    }
    async with httpx.AsyncClient() as client:
        timeout = httpx.Timeout(60.0, connect=60.0)
        response = await client.get('https://login.taobao.com/jump', params=params, headers=headers,
                                    timeout=timeout, follow_redirects=False)
        cookies = response.cookies
        cookies_list = [{"name": k, "value": v} for k, v in cookies.items()]
        update_cookie(cookies_list)


async def get_cna() -> None:
    async with httpx.AsyncClient() as client:
        timeout = httpx.Timeout(60.0, connect=60.0)
        timestamp = str(int(time.time() * 1000))
        response = await client.get(f"https://log.mmstat.com/eg.js?t={timestamp}", headers=headers, timeout=timeout)
        cookies = response.cookies
        cookies_list = [{"name": k, "value": v} for k, v in cookies.items()]
        update_cookie(cookies_list)


async def api_request(
        req_type: str,
        api: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        req_body: Optional[Dict[str, Any]] = None,
        _m_h5_tk: Optional[str] = 'undefined'
) -> Dict[str, Any] | str | None:
    """
    用于发送API请求并获取响应数据
    参数:
    api (str): 请求的API地址。
    params (Dict[str, Any]): 请求参数字典，注意请求参数中的t需要严格和用来签名获取sign的时间戳一致，否则鉴权失败。
    data (str): 用于生成签名的数据。
    _m_h5_tk (Optional[str]): 用于签名的参数值，来自响应cookie，如果未提供则默认为'undefined'。
    """
    async with httpx.AsyncClient() as client:
        timeout = httpx.Timeout(60.0, connect=60.0)
        sign_dict = get_sign_params(_m_h5_tk, data)

        if _m_h5_tk == 'undefined':
            logger.info(f"初始化sign参数: {sign_dict}")
        else:
            logger.info(f"获取sign参数: {sign_dict}")

        # 添加签名参数到请求参数中
        params['t'] = sign_dict['t']
        params['sign'] = sign_dict['sign']

        if req_type == 'POST':
            req_body['data'] = data
            response = await client.post(api, data=req_body, params=params, headers=headers, timeout=timeout)
        else:
            response = await client.get(api, params=params, headers=headers, timeout=timeout)

        # 如果是首次请求，需要从响应中获取_m_h5_tk和_m_h5_tk_enc
        if _m_h5_tk == 'undefined':
            cookies = response.cookies
            cookies_list = [{"name": k, "value": v} for k, v in cookies.items()]
            _m_h5_tk = cookies.get('_m_h5_tk', '')
            update_cookie(cookies_list)
            logger.info(f"获取token参数: {dict(cookies)}")
            return _m_h5_tk

        content = response.text
        if content.startswith('{'):
            return response.json()
        else:
            return jsonp_to_json(content)


async def fetch_company_data(store_id: str) -> Dict[str, Any] | None:
    """
    获取1688店铺企业信息。

    参数:
    data (str): 请求所需的数据，通常为JSON格式的字符串。

    返回:
    Dict[str, Any] | None: 解析后的JSON数据，如果请求失败则为None。
    """

    # 请求参数中data对应的数据
    data = '{"componentKey":"wp_pc_shop_basic_info","params":"{\\"memberId\\":\\"' + store_id + '\\"}"}'

    params = {
        'jsv': JS_VERSION,
        'appKey': APP_KEY,
        't': '',
        'sign': '',
        'api': 'mtop.alibaba.alisite.cbu.server.pc.ModuleAsyncService',
        'v': '1.0',
        'type': 'jsonp',
        'valueType': 'string',
        'dataType': 'jsonp',
        'timeout': '10000',
        'callback': 'mtopjsonp1',
        'data': data
    }

    # API请求地址
    api = 'https://h5api.m.1688.com/h5/mtop.alibaba.alisite.cbu.server.pc.moduleasyncservice/1.0/'

    # 首次请求，获取_m_h5_tk
    _m_h5_tk = await api_request('GET', api, params, data)

    # 使用获取到的_m_h5_tk发送实际的数据请求
    response_data = await api_request('GET', api, params, data, _m_h5_tk=_m_h5_tk)
    logger.info(f"返回数据:{response_data}")
    return response_data


async def init() -> None:
    # 初始化cookies参数值
    await get_cna()
    await get_tb_token()


if __name__ == '__main__':
    import asyncio

    # 示例：请求1688店铺企业信息接口获取店铺信息
    member_id = 'b2b-22133374292418351a'  # 店铺ID
    asyncio.run(init())
    asyncio.run(fetch_company_data(member_id))
