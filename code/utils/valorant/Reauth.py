import traceback
from botpy.message import Message,DirectMessage
from aiohttp import client_exceptions
from .EzAuth import EzAuth, EzAuthExp
from ..file.Files import UserAuthCache,UserPwdReauth,_log
from .Val import fetch_valorant_point,loginStat
from .. import Gtime


# 检查aiohttp错误的类型
def client_exceptions_handler(result:str,err_str:str) -> str:
    if 'auth.riotgames.com' and '403' in result:
        global loginStat
        loginStat.Login_Forbidden = True
        err_str += f"[check_reauth] 403 err! set LoginForbidden = True"
    elif '404' in result:
        err_str += f"[check_reauth] 404 err! network err, try again"
    else:
        err_str += f"[check_reauth] Unkown aiohttp ERR!"

    return err_str

# cookie重新登录
async def login_reauth(user_id: str, riot_user_id: str) -> bool:
    """Return:
    - True: reauthorize success
    - False: reauthorize failed
    """
    base_print = f"Au:{user_id} | Riot:{riot_user_id} | "
    _log.info(base_print + "auth_token failure,trying reauthorize()")
    global UserAuthCache
    # 这个函数只负责重登录，所以直接找对应的拳头用户id
    auth = UserAuthCache['data'][riot_user_id]['auth']
    assert isinstance(auth, EzAuth)
    #用cookie重新登录,会返回一个bool是否成功
    ret = await auth.reauthorize()
    if ret:  #会返回一个bool是否成功,成功了重新赋值
        UserAuthCache['data'][riot_user_id]['auth'] = auth
        _log.info(base_print + "reauthorize() Successful!")
    else:  # cookie重新登录失败
        _log.info(base_print + "reauthorize() Failed! T-T")  # 失败打印
        # 有保存账户密码+不是邮箱验证用户
        if riot_user_id in UserAuthCache['acpw'] and (not UserAuthCache[riot_user_id]['2fa']):
            auth = EzAuth()  # 用账户密码重新登录
            resw = await auth.authorize(UserAuthCache['acpw'][riot_user_id]['a'],
                                        UserAuthCache['acpw'][riot_user_id]['p'])
            if not resw['status']:  # 需要邮箱验证，那就直接跳出
                _log.info(base_print + "authorize() need 2fa, return False")
                return False
            # 更新auth对象
            UserAuthCache['data'][riot_user_id]['auth'] = auth
            auth.save_cookies(f"./log/cookie/{riot_user_id}.cke")  # 保存cookie
            # 记录使用账户密码重新登录的时间，和对应的账户
            UserPwdReauth[user_id][Gtime.GetTime()] = f"{auth.Name}#{auth.Tag}"
            _log.info(base_print + "authorize by account/passwd")
            ret = True
    # 正好返回auth.reauthorize()的bool
    return ret


# 判断是否需要重新获取token
async def check_reauth(def_name: str,
                       user_id: str,
                       riot_user_id: str,
                       msg: Message | DirectMessage = None) -> bool | dict[str, str]:  # type: ignore
    """Args:
    - def_name: def_name call this def
    - user_id: platfrom user_id
    - riot_user_id: which riot account for reauth
    - debug_ch: channel for sending debug info
    - msg: khl.Message obj, only send info if msg != None

    Return value:
     - True: no need to reauthorize / get `user_id` as params & reauhorize success 
     - False: unkown err / reauthorize failed
     - send_msg(dict): get `Message` as params & reauhorize success
    """
    try:
        at_text = f"<@{user_id}>\n"
        # 1.通过riot用户id获取对象
        auth = UserAuthCache['data'][riot_user_id]['auth']
        assert isinstance(auth, EzAuth)
        # 2.直接从对象中获取user的Token，并尝试获取用户的vp和r点
        riotUser = auth.get_riotuser_token()
        resp = await fetch_valorant_point(riotUser)
        # resp={'httpStatus': 400, 'errorCode': 'BAD_CLAIMS', 'message': 'Failure validating/decoding RSO Access Token'}
        # 3.如果没有这个键，会直接报错进except; 如果有这个键，就可以继续执行下面的内容
        test = resp['httpStatus']
        # 3.1 走到这里代表需要重登

        # # 3.2 如果传入params有消息对象msg，则提示用户
        # if msg: # 由于这个几乎每次都会出现，干脆取消
        #     text = f"{at_text}获取「{def_name}」失败！正在尝试重新获取token，您无需操作"
        #     await msg.reply(content=f"{text}\n{resp['message']}")

        # 4.传入user id和拳头账户id，进行重登
        ret = await login_reauth(user_id, auth.user_id)
        # ret为False，重登失败，发送提示信息
        if not ret and msg:
            text = f"{at_text}重新获取token失败，请私聊「/login」重新登录\n"
            await msg.reply(content=f"{text}\nreauthorize failed")
            return False

        return ret  #返回是否成功重登
    # aiohttp网络错误
    except client_exceptions.ClientResponseError as result:
        err_str = f"Au:{user_id} | aiohttp ERR!\n```\n{traceback.format_exc()}\n```\n"
        err_str = client_exceptions_handler(str(result),err_str)
        _log.error(err_str)
        if msg: msg.reply(content=f"{at_text}出现错误！reauth:\naiohttp.client_exceptions.ClientResponseError")
        return False
    # 用户在EzAuth初始化完毕之前调用了其他命令
    except EzAuthExp.InitNotFinishError as result:
        _log.warning(f"Au:{user_id} | EzAuth used before init")
        return False
    except Exception as result:
        if 'httpStatus' in str(result):
            _log.info(f"Au:{user_id} | No need to reauthorize [{result}]")
            return True
        else:
            if msg: msg.reply(content=f"{at_text}出现错误！reauth:\n{result}")
            _log.exception("Unkown Exception occur")
            return False