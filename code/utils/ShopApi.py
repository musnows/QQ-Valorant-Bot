import json
import os
import aiohttp

from utils.FileManage import bot_config

# 自己的api的root url
rootUrl = bot_config["val_api_url"]
apiToken = bot_config["val_api_token"]

# 商店获取(直接登录)
async def shop_url_post(account:str,passwd:str,img_src='',img_ratio='0'):
    url = rootUrl + "/shop-url"
    params = {
        "token":apiToken,
        "account": account,
        "passwd": passwd,
        "img_src": img_src,
        "img_ratio": img_ratio
    }
    async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                res = json.loads(await response.text())
    return res

# 邮箱验证
async def tfa_code_post(account:str,vcode:str):
    url = rootUrl + "/tfa"
    params = {
        "token":apiToken,
        "account": account,
        "vcode": vcode
    }
    async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                res = json.loads(await response.text())
    return res