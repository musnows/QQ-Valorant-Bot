# 缓存登录对象
from .EzAuth import EzAuth
from ..file.Files import UserAuthCache,_log

Auth2faCache = UserAuthCache['tfa']
"""UserAuthCache['tfa']"""
LOGIN_LIMITED = 3
"""每个用户只能登录3个账户"""

def check_login_num(user_id:str) -> bool:
    """检查已登录账户的数量
    - False 超出限制
    - True  未超出
    """
    if user_id in UserAuthCache["qqbot"]:
        if len(UserAuthCache["qqbot"][user_id])>=LOGIN_LIMITED:
            return False
        else:
            return True
    else:
        return True

async def cache_auth_object(platfrom:str,key:str,auth:EzAuth) -> None:
    """cache auth obj base on platform and key
    - platfrom: qqbot
    - key: qq_user_id
    - auth: EzAuth obj
    """
    _log.debug(f"enter def | {UserAuthCache}")
    # 如果是2fa用户，且键值不在缓存里面，认为是初次登录，需要提供邮箱验证码
    if auth.is2fa and key not in Auth2faCache:
        Auth2faCache[key] = auth # 将对象插入2fa的缓存
        return
    # 如果键值存在，认为是tfa登陆成功，删除临时键值
    elif auth.is2fa and key in Auth2faCache:
        del Auth2faCache[key]
    
    # 如果对象没有成功初始化，说明还是有问题；不进行缓存，让用户重登
    if not auth.is_init():
        _log.warning(f"key:{key} | auth obj not init!")
        return

    # 在data中插入对象
    UserAuthCache['data'][auth.user_id] = {"auth": auth, "2fa": auth.is2fa}

    # 判断缓存的来源
    if platfrom == 'qqbot':
        # 用户id键值不存在，新建key
        if key not in UserAuthCache['qqbot']:
            UserAuthCache['qqbot'][key] = []
        # 如果该账户已经登陆过了，则不进行操作
        if auth.user_id not in UserAuthCache['qqbot'][key]:
            UserAuthCache['qqbot'][key].append(auth.user_id) # 往用户id缓存list中插入Riot用户的uuid
    
    _log.debug(f"exit def | {UserAuthCache}")

async def get_tfa_auth_object(key:str) -> EzAuth | None:
    """get auth obj (need 2fa verify code) base on key. Return None if key not in cache
    """
    _log.debug(f"enter def | {Auth2faCache}")
    if key not in Auth2faCache:
        return None
    else:
        return Auth2faCache[key]
    
async def get_auth_object(platfrom:str,key:str) -> list[dict[str,EzAuth]]|None:
    """get auth obj base on key. Return None if key not in cache
    - platfrom: qqbot
    - key: qq_user_id
    """
    ret = list()
    if platfrom=="qqbot":
        _log.debug(f"enter def | {UserAuthCache}")
        if key not in UserAuthCache["qqbot"]:
            _log.info(f"platfrom: {platfrom} | key:{key} not in cache")
            return ret
        
        riot_user_id_list = UserAuthCache["qqbot"][key]
        for ru in riot_user_id_list:
            ret.append(UserAuthCache["data"][ru])
        
        return ret
    else:
        _log.error(f"platfrom '{platfrom}' invalid")
        return ret