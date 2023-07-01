import json
import aiohttp,copy
from ..file.Files import api_config,_log

# 自己的api的root url
rootUrl = api_config["val_api_url"]
apiToken = api_config["val_api_token"]

# 图片获取器
async def img_requestor(img_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(img_url) as r:
            return await r.read()

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

# 通过商店皮肤uuid list获取图片
async def shop_draw_get(list_shop:list,vp='0',rp='0',img_src='',img_ratio='0'):
    # 死循环，出错采用备用api
    global rootUrl
    rUrl = copy.deepcopy(rootUrl)
    for i in range(5):
        try:
            url = rUrl + "/shop-draw"
            params = {
                "token":apiToken,
                "list_shop": list_shop,
                "vp":vp,
                "rp":rp,
                "img_src": img_src,
                "img_ratio": img_ratio
            }
            async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        res = json.loads(await response.text())
            res['type'] = 'url'
            return res
        except Exception as result:
            if i >=3: raise result # 超过3次重试，直接跳出
            # 没有办法链接到api
            err_cur = str(result)
            # 出现aiohttp错误，或者是json解析错误
            if "Cannot connect to host" in err_cur or "Expecting value: line 1" in err_cur:
                # 如果rootUrl是不是备用的，那就改成本地（反过来也一样）
                rUrl = api_config["val_api_url"] if rUrl == api_config["val_api_url_bak"] else api_config["val_api_url_bak"]
                _log.info(f"[ConnectError] {result} - [rootUrl] swap to {rUrl}")
            else:
                raise result
            
# 早八更新比较
import requests
def shop_cmp_post(best:dict,worse:dict,platform:str='qqchannel'):
    url = rootUrl + "/shop-cmp"
    params = {
        "token":apiToken,
        "best":best,
        "worse":worse,
        "platform":platform
    }
    res = requests.post(url,json=params) # 请求api
    return res