import json
import os
import aiohttp
from botpy.ext.cog_yaml import read

bot_config = read(os.path.join(os.path.dirname(__file__), "./config/config.yaml"))

# 自己的api的root url
rootUrl = bot_config["val_api_url"]
apiToken = bot_config["val_api_token"]

# help命令文字
def help_text():
    text = "以下为bot的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+= "「@机器人 /shop」查询商店\n"
    text+= "「@机器人 /uinfo」查询用户vp/rp/等级\n"
    return text


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