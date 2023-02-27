import json
import io
import aiohttp,copy
from PIL import Image
from utils.FileManage import bot_config,_log

# 自己的api的root url
rootUrl = bot_config["val_api_url"]
apiToken = bot_config["val_api_token"]


# 图片获取器
async def img_requestor(img_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(img_url) as r:
            return await r.read()

# 存本地再打开(很蠢但是没办法)
async def shop_img_load(img_src:str,key:str):
    # 存本地
    img_path = f"./log/img/{key}.png"
    image = Image.open(io.BytesIO(await img_requestor(img_src)))
    image.save(img_path,format='PNG')
    # 再打开上传
    with open(img_path, "rb") as img:
        img_bytes = img.read()
    return img_bytes

# 测试用
async def shop_img_test(message):
    img = io.BytesIO(await img_requestor('https://img.kookapp.cn/assets/2022-09/lSj90Xr9yA0zk0k0.png'))
    bg = Image.open(img)  # 16-9 商店默认背景
    imgByteArr = io.BytesIO(bg.tobytes())
    #img_bytes = bg.tobytes()
    img_bytes = img.read()
    # 只有下面这个办法可行
    # with open("./test.png", "rb") as img:
    #     img_bytes = img.read()
    print(type(img_bytes))
    print(type(img.read()))

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
    i = 0
    global rootUrl
    rUrl = copy.deepcopy(rootUrl)
    while True:
        try:
            i+=1
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
            return res
        except Exception as result:
            if i >=3: raise result # 超过3次重试，直接跳出
            # 没有办法链接到api
            err_cur = str(result)
            # 出现aiohttp错误，或者是json解析错误
            if "Cannot connect to host" in err_cur or "Expecting value: line 1" in err_cur:
                # 如果rootUrl是不是备用的，那就改成本地（反过来也一样）
                rUrl = bot_config["val_api_url"] if rUrl == bot_config["val_api_url_bak"] else bot_config["val_api_url_bak"]
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