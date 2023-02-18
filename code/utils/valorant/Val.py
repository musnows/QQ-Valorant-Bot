# encoding: utf-8:
import json
import aiohttp
from khl import Bot, Message
from khl.card import Card, CardMessage, Element, Module, Types

# 预加载文件
from utils.FileManage import ValBundleList, ValItersList, ValPriceList, ValSkinList
SKIN_ICON_ERR = "https://img.kookapp.cn/assets/2023-02/ekwdy7PiQC0e803m.png"
X_RIOT_CLIENTVERSION = "release-06.01-shipping-8-820493" 


###################################### local files search ######################################################


#从list中获取价格
def fetch_item_price_bylist(item_id):
    for item in ValPriceList['Offers']:  #遍历查找指定uuid
        if item_id == item['OfferID']:
            return item


#从list中获取等级(这个需要手动更新)
def fetch_item_iters_bylist(iter_id):
    for iter in ValItersList['data']:  #遍历查找指定uuid
        if iter_id == iter['uuid']:
            res = {'data': iter}  #所以要手动创建一个带data的dict作为返回值
            return res


#从list中获取皮肤
def fetch_skin_bylist(item_id):
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
def fetch_skin_list_byname(name):
    wplist = list()  #包含该名字的皮肤list
    for skin in ValSkinList['data']:
        if name in skin['displayName']:
            data = {'displayName': skin['displayName'], 'lv_uuid': skin['levels'][0]['uuid']}
            wplist.append(data)
    return wplist


#从list中通过皮肤lv0uuid获取皮肤等级
def fetch_skin_iters_bylist(item_id):
    for it in ValSkinList['data']:
        if it['levels'][0]['uuid'] == item_id:
            res_iters = fetch_item_iters_bylist(it['contentTierUuid'])
            return res_iters


# 用名字查询捆绑包包含什么枪
async def fetch_bundle_weapen_byname(name):
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
async def fetch_user_gameID(auth):
    url = "https://pd.ap.a.pvp.net/name-service/v2/players"
    payload = json.dumps([auth['auth_user_id']])
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": auth['entitlements_token'],
        "Authorization": "Bearer " + auth['access_token']
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, data=payload) as response:
            res = json.loads(await response.text())
    return res


# 获取每日商店
async def fetch_daily_shop(u):
    url = "https://pd.ap.a.pvp.net/store/v2/storefront/" + u['auth_user_id']
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token']
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())
    return res


# Api获取玩家的vp和r点
async def fetch_valorant_point(u):
    url = "https://pd.ap.a.pvp.net/store/v1/wallet/" + u['auth_user_id']
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token']
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())
    return res


# 获取vp和r点的dict
async def fetch_vp_rp_dict(u):
    """{'vp': vp, 'rp': rp}
    """
    resp = await fetch_valorant_point(u)
    vp = resp["Balances"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]  #vp
    rp = resp["Balances"]["e59aa87c-4cbf-517a-5983-6e81511be9b7"]  #R点
    return {'vp': vp, 'rp': rp}


# 获取商品价格（所有）
async def fetch_item_price_all(u):
    url = "https://pd.ap.a.pvp.net/store/v1/offers/"
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token']
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res


# 获取商品价格（用uuid获取单个价格）
async def fetch_item_price_uuid(u, item_id: str):
    res = await fetch_item_price_all(u)  #获取所有价格

    for item in res['Offers']:  #遍历查找指定uuid
        if item_id == item['OfferID']:
            return item

    return "0"  #没有找到


# 获取皮肤等级（史诗/传说）
async def fetch_item_iters(iters_id: str):
    url = "https://valorant-api.com/v1/contenttiers/" + iters_id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_iters = json.loads(await response.text())

    return res_iters


# 获取所有皮肤
async def fetch_skins_all():
    url = "https://valorant-api.com/v1/weapons/skins"
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_skin = json.loads(await response.text())

    return res_skin


# 获取所有皮肤捆绑包
async def fetch_bundles_all():
    url = "https://valorant-api.com/v1/bundles"
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_bundle = json.loads(await response.text())

    return res_bundle


# 获取获取玩家当前装备的卡面和称号
async def fetch_player_loadout(u):
    url = f"https://pd.ap.a.pvp.net/personalization/v2/players/{u['auth_user_id']}/playerloadout"
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token'],
        'Connection': 'close'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res


# 获取合约（任务）进度
# client version from https://valorant-api.com/v1/version
async def fetch_player_contract(u):
    #url="https://pd.ap.a.pvp.net/contract-definitions/v2/definitions/story"
    url = f"https://pd.ap.a.pvp.net/contracts/v1/contracts/" + u['auth_user_id']
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token'],
        "X-Riot-ClientPlatform":
        "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
        "X-Riot-ClientVersion": X_RIOT_CLIENTVERSION
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            res = json.loads(await response.text())

    return res

# 获取玩家的等级信息
async def  fetch_player_level(u):
    url = "https://pd.ap.a.pvp.net/account-xp/v1/players/"+ u['auth_user_id']
    headers = {
        "Content-Type": "application/json",
        "X-Riot-Entitlements-JWT": u['entitlements_token'],
        "Authorization": "Bearer " + u['access_token'],
    }
    async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                res = json.loads(await response.text())

    return res

# 获取玩家当前通行证情况，uuid
async def fetch_contract_uuid(id):
    url = "https://valorant-api.com/v1/contracts/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_con = json.loads(await response.text())

    return res_con


# 获取玩家卡面，uuid
async def fetch_playercard_uuid(id):
    url = "https://valorant-api.com/v1/playercards/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_card = json.loads(await response.text())

    return res_card


# 获取玩家称号，uuid
async def fetch_title_uuid(id):
    url = "https://valorant-api.com/v1/playertitles/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_title = json.loads(await response.text())

    return res_title


# 获取喷漆，uuid
async def fetch_spary_uuid(id):
    url = "https://valorant-api.com/v1/sprays/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_sp = json.loads(await response.text())

    return res_sp


# 获取吊坠，uuid
async def fetch_buddies_uuid(id):
    url = "https://valorant-api.com/v1/buddies/levels/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_sp = json.loads(await response.text())

    return res_sp


# 获取皮肤，通过lv0的uuid
async def fetch_skinlevel_uuid(id):
    url = f"https://valorant-api.com/v1/weapons/skinlevels/" + id
    headers = {'Connection': 'close'}
    params = {"language": "zh-TW"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            res_skin = json.loads(await response.text())
    return res_skin