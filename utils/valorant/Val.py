# encoding: utf-8:
import json
import aiohttp
import time

# 预加载文件
from .EzAuth import X_RIOT_CLIENTVERSION,X_RIOT_CLIENTVPLATFROM,RiotUserToken
from ..file.Files import ValItersList, ValPriceList, ValSkinList
SKIN_ICON_ERR = "https://img.kookapp.cn/assets/2023-02/ekwdy7PiQC0e803m.png"

# 检测登录状态
class LoginStatus:
    # 公有成员
    RATE_LIMITED_TIME = 180  # 全局登录速率超速等待秒数
    # 构造函数
    def __init__(self) -> None:
        # 全局的速率限制，如果触发了速率限制的err，则阻止所有用户login
        self.ratelimit = {'limit': False, 'time': time.time()}
        self.Login_Forbidden = True  # 403错误禁止登录
    
    # 检查全局用户登录速率
    def checkRate(self) -> bool:
        """- True: good to go
           - False: rate limited
        """
        if self.ratelimit['limit']:
            if (time.time() - self.ratelimit['time']) > self.RATE_LIMITED_TIME:
                self.ratelimit['limit'] = False  # 超出限制时间，解除
            else:  # 未超出限制时间
                return False
        # 没有limit 或 已经超出了限制时间
        return True

    # 检查是否出现了403错误
    def checkForbidden(self) -> bool:
        """- True: good to go
           - False: forbidden 
        """
        return self.Login_Forbidden

    # 检查是否可以进行登录（登录速率和forbidden都不行）
    def Bool(self) -> bool:
        return self.checkForbidden() and self.checkRate()

    # 出现了速率限制，设置
    def setRateLimit(self) -> None:
        self.ratelimit = {'limit': True, 'time': time.time()}

    # 出现了403错误，设置
    def setForbidden(self) -> None:
        if self.Login_Forbidden:
            self.Login_Forbidden = False
        else:
            self.Login_Forbidden = True

    # 拳头api调用被禁止的时候用这个变量取消所有相关命令
    async def sendForbidden(self,msg) -> None:
        await msg.reply(
            content=f"拳头api登录接口出现了一些错误，已禁止所有相关功能的使用；\n如有疑问，请联系开发者"
        )

# 实例化一个对象
loginStat = LoginStatus()

###################################### local files search ######################################################


#从list中获取价格
def fetch_item_price_bylist(item_id) -> dict:
    for item in ValPriceList['Offers']:  #遍历查找指定uuid
        if item_id == item['OfferID']:
            return item
    return {}

#从list中获取等级(这个需要手动更新)
def fetch_item_iters_bylist(iter_id) -> dict:
    res = {}
    for iter in ValItersList['data']:  #遍历查找指定uuid
        if iter_id == iter['uuid']:
            res = {'data': iter}  #所以要手动创建一个带data的dict作为返回值
    return res


#从list中获取皮肤
def fetch_skin_bylist(item_id) -> dict: 
    res = {}  #下面我们要操作的是获取通行证的皮肤，但是因为遍历的时候已经跳过data了，返回的时候就不好返回
    for item in ValSkinList['data']:  #遍历查找指定uuid
        if item_id == item['levels'][0]['uuid']:
            res['data'] = item  #所以要手动创建一个带data的dict作为返回值
            # 可能出现图标为空的情况（异星霸主 斗牛犬）
            while(res['data']['displayIcon']==None): 
                for level in item['levels']: # 在等级里面找皮肤图标
                    if level["displayIcon"] != None:
                        res['data']['displayIcon'] = level["displayIcon"]
                        break # 找到了，退出循环
                # 没找到，替换成err图片
                res['data']['displayIcon'] = SKIN_ICON_ERR
            
    return res


#从list中，通过皮肤名字获取皮肤列表
def fetch_skin_list_byname(name) ->list[dict]:
    wplist = list()  #包含该名字的皮肤list
    for skin in ValSkinList['data']:
        if name in skin['displayName']:
            data = {'displayName': skin['displayName'], 'lv_uuid': skin['levels'][0]['uuid']}
            wplist.append(data)
    return wplist


#从list中通过皮肤lv0uuid获取皮肤等级
def fetch_skin_iters_bylist(item_id) -> dict:
    res_iters = {}
    for it in ValSkinList['data']:
        if it['levels'][0]['uuid'] == item_id:
            res_iters = fetch_item_iters_bylist(it['contentTierUuid'])
    return res_iters


# 用名字查询捆绑包包含什么枪
async def fetch_bundle_weapen_byname(name)->list[dict]:
    # 捆绑包的所有皮肤
    WeapenList = list()
    for skin in ValSkinList['data']:
        if name in skin['displayName']:
            # 为了方便查询价格，在这里直接把skin的lv0-uuid也给插入进去
            data = {'displayName': skin['displayName'], 'lv_uuid': skin['levels'][0]['uuid']}
            WeapenList.append(data)

    return WeapenList


####################################################################################################
###################https://github.com/HeyM1ke/ValorantClientAPI#####################################
####################################################################################################


#获取用户游戏id(从使用对象修改成使用文件中的内容)
async def fetch_user_gameID(ru:RiotUserToken) -> dict:
    url = "https://pd.ap.a.pvp.net/name-service/v2/players"
    payload = json.dumps([ru.user_id])
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=payload) as response:
            res = json.loads(await response.text())
    return res


# 获取每日商店
async def fetch_daily_shop(ru:RiotUserToken)-> dict:
    url = "https://pd.ap.a.pvp.net/store/v2/storefront/" + ru.user_id
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())
    return res


# Api获取玩家的vp和r点
async def fetch_valorant_point(ru:RiotUserToken)-> dict:
    url = "https://pd.ap.a.pvp.net/store/v1/wallet/" + ru.user_id
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())
    return res


# 获取vp和r点的dict
async def fetch_vp_rp_dict(ru:RiotUserToken)-> dict[str,int]:
    resp = await fetch_valorant_point(ru)
    vp = resp["Balances"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]  #vp
    rp = resp["Balances"]["e59aa87c-4cbf-517a-5983-6e81511be9b7"]  #R点
    return {'vp': vp, 'rp': rp}


# 获取商品价格（所有）
async def fetch_item_price_all(ru:RiotUserToken)-> dict:
    url = "https://pd.ap.a.pvp.net/store/v1/offers/"
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res


# 获取商品价格（用uuid获取单个价格）
async def fetch_item_price_uuid(ru:RiotUserToken, item_id: str)-> str:
    res = await fetch_item_price_all(ru)  #获取所有价格

    for item in res['Offers']:  #遍历查找指定uuid
        if item_id == item['OfferID']:
            return item

    return "0"  #没有找到


# 获取皮肤等级（史诗/传说）
async def fetch_item_iters(iters_id: str)-> dict:
    url = "https://valorant-api.com/v1/contenttiers/" + iters_id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_iters = json.loads(await response.text())

    return res_iters


# 获取所有皮肤
async def fetch_skins_all()->dict:
    url = "https://valorant-api.com/v1/weapons/skins"
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_skin = json.loads(await response.text())

    return res_skin


# 获取所有皮肤捆绑包
async def fetch_bundles_all()->dict:
    url = "https://valorant-api.com/v1/bundles"
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_bundle = json.loads(await response.text())

    return res_bundle


# 获取获取玩家当前装备的卡面和称号
async def fetch_player_loadout(ru:RiotUserToken)->dict:
    url = f"https://pd.ap.a.pvp.net/personalization/v2/players/{ru.user_id}/playerloadout"
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token,
        'Connection': 'close'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res


# 获取合约（任务）进度
async def fetch_player_contract(ru:RiotUserToken)->dict:
    #url="https://pd.ap.a.pvp.net/contract-definitions/v2/definitions/story"
    url = f"https://pd.ap.a.pvp.net/contracts/v1/contracts/" + ru.user_id
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token,
        "X-Riot-ClientPlatform": X_RIOT_CLIENTVPLATFROM,
        "X-Riot-ClientVersion": X_RIOT_CLIENTVERSION
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res

# 获取玩家的等级信息
async def  fetch_player_level(ru:RiotUserToken) -> dict:
    url = "https://pd.ap.a.pvp.net/account-xp/v1/players/"+ ru.user_id
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": ru.entitlements_token,
        "Authorization": "Bearer " + ru.access_token,
    }
    async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                res = json.loads(await response.text())

    return res

# 获取玩家当前通行证情况，uuid
async def fetch_contract_uuid(id:str) -> dict:
    url = "https://valorant-api.com/v1/contracts/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_con = json.loads(await response.text())

    return res_con


# 获取玩家卡面，uuid
async def fetch_playercard_uuid(id:str)-> dict:
    url = "https://valorant-api.com/v1/playercards/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_card = json.loads(await response.text())

    return res_card


# 获取玩家称号，uuid
async def fetch_title_uuid(id:str)-> dict:
    url = "https://valorant-api.com/v1/playertitles/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_title = json.loads(await response.text())

    return res_title


# 获取喷漆，uuid
async def fetch_spary_uuid(id:str)-> dict:
    url = "https://valorant-api.com/v1/sprays/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_sp = json.loads(await response.text())

    return res_sp


# 获取吊坠，uuid
async def fetch_buddies_uuid(id:str)->dict:
    url = "https://valorant-api.com/v1/buddies/levels/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_sp = json.loads(await response.text())

    return res_sp


# 获取皮肤，通过lv0的uuid
async def fetch_skinlevel_uuid(id:str)->dict:
    url = f"https://valorant-api.com/v1/weapons/skinlevels/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_skin = json.loads(await response.text())
    return res_skin