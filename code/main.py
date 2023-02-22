# -*- coding: utf-8 -*-
import time
import threading
import traceback
import os

import botpy
from botpy import logging
from aiohttp import client_exceptions

from botpy.message import Message,DirectMessage
from botpy.types.message import MarkdownPayload
from utils.FileManage import bot_config,UserTokenDict,UserAuthDict,UserApLog,save_all_file
from utils.valorant.ShopApi import *
from utils.valorant.Val import fetch_daily_shop,fetch_vp_rp_dict,fetch_valorant_point
from utils.valorant.EzAuth import EzAuthExp,Get2faWait_Key,auth2faWait,auth2fa,authflow,User2faCode
from utils.Gtime import GetTime
from utils.Channel import listenConf

# 日志
_log = logging.get_logger()
Login_Forbidden = False

# help命令文字
def help_text(bot_id:str):
    text = "以下为bot的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+=f"「<@{bot_id}> /shop」查询商店\n"
    text+=f"「<@{bot_id}> /uinfo」查询用户vp/rp/等级\n"
    text+=f"「<@{bot_id}> /pm」发起私信会话\n"
    return text

# cookie重新登录
async def login_reauth(user_id: str):
    base_print = f"[{GetTime()}] Au:{user_id} = "
    _log.info(base_print + "auth_token failure,trying reauthorize()")
    global UserAuthDict,UserTokenDict
    auth = UserAuthDict[user_id]['auth']
    #用cookie重新登录,会返回一个bool是否成功
    ret = await auth.reauthorize()
    if ret:  #会返回一个bool是否成功,成功了重新赋值
        UserAuthDict[user_id]['auth'] = auth
        _log.info(base_print + "reauthorize() Successful!")
    else:  # cookie重新登录失败
        _log.info(base_print + "reauthorize() Failed! T-T")  # 失败打印
        # 有保存账户密码+不是邮箱验证用户
        if user_id in UserAuthDict['AP'] and (not UserAuthDict[user_id]['2fa']):
            res_auth = await authflow(UserAuthDict['AP'][user_id]['a'], UserAuthDict['AP'][user_id]['p'])
            UserAuthDict[user_id]['auth'] = res_auth  # 用账户密码重新登录
            res_auth._cookie_jar.save(f"./log/cookie/{user_id}.cke")  #保存cookie
            # 记录使用账户密码重新登录的时间
            UserApLog[user_id][GetTime()] = UserTokenDict[user_id]['GameName']
            _log.info(base_print + "authflow() by AP")
            ret = True
    # 正好返回auth.reauthorize()的bool
    return ret  


# 判断是否需要重新获取token
async def check_reauth(def_name: str = "", msg = None):
    """
    return value:
     - True: no need to reauthorize / get `user_id` as params & reauhorize success 
     - False: unkown err / reauthorize failed
    """
    user_id = "[ERR!]"  # 先给userid赋值，避免下方打印的时候报错（不出意外是会被下面的语句修改的）
    # 判断传入的类型是不是消息 (公屏，私聊)
    is_msg = isinstance(msg, Message) or isinstance(msg,DirectMessage) 
    try:
        # 如果是str就直接用,是msg对象就用id
        user_id = msg.author.id  if is_msg else msg
        _log.info("check reauth: ",user_id)
        # 找键值，获取auth对象
        auth = UserAuthDict[user_id]['auth']
        userdict = {
            'auth_user_id': auth.user_id,
            'access_token': auth.access_token,
            'entitlements_token': auth.entitlements_token
        }
        # 调用riot api测试cookie是否过期
        resp = await fetch_valorant_point(userdict)
        # {'httpStatus': 400, 'errorCode': 'BAD_CLAIMS', 'message': 'Failure validating/decoding RSO Access Token'}
        # 如果没有这个键，会直接报错进except（代表没有错误）
        # 如果有这个键，就可以继续执行下面的内容（代表cookie过期了）
        key_test = resp['httpStatus']
        # 如果传入的是msg，则提示用户
        if is_msg:  
            text = f"获取「{def_name}」失败！正在尝试重新获取token，您无需操作"
            await msg.reply(content=f"{text}\n{resp['message']}")
        # 不管传入的是用户id还是msg，都传user_id进入该函数
        ret = await login_reauth(user_id)
        if ret == False and is_msg:  #没有正常返回,重新获取token失败
            text = f"重新获取token失败，请私聊「/login」重新登录\n"
            await msg.reply(content=f"{text}\nAuto Reauthorize Failed!")
        # 返回真/假
        return ret 
    except client_exceptions.ClientResponseError as result:
        err_str = f"[Check_re_auth] aiohttp ERR!\n```\n{traceback.format_exc()}\n```\n"
        if 'auth.riotgames.com' and '403' in str(result):
            global Login_Forbidden
            Login_Forbidden = True
            err_str += f"[Check_re_auth] 403 err! set Login_Forbidden = True"
        elif '404' in str(result):
            err_str += f"[Check_re_auth] 404 err! network err, try again"
        else:
            err_str += f"[Check_re_auth] Unkown aiohttp ERR!"
        # 登陆失败
        if is_msg: msg.reply(f"出现错误！check_reauth:\naiohttp client_exceptions ClientResponseError")
        _log.info(err_str)
        return False
    except Exception as result:
        if 'httpStatus' in str(result):
            _log.info(f"[Check_re_auth] Au:{user_id} No need to reauthorize [{result}]")
            return True
        else:
            if is_msg: msg.reply(f"出现错误！check_reauth:\n{result}")
            _log.info(f"[Check_re_auth] Unkown ERR!\n{traceback.format_exc()}")
            return False

# bot main
class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    
    # 登录命令
    async def login_cmd(self,msg:Message,account:str,passwd:str):
        _log.info(f"[login] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")
        global login_rate_limit,UserAuthDict,UserTokenDict,Login_Forbidden
        try:
            # 1.检查全局登录速率
            await check_global_loginRate()  # 无须接收此函数返回值，直接raise
            # 2.发送开始登录的提示消息
            await msg.reply(content=f"正在获取您的账户token和cookie")

            # 3.登录，获取用户的token
            key = msg.author.id # 用用户id做key
            # 如果使用异步运行该函数，执行流会被阻塞住等待，应该使用线程来操作
            th = threading.Thread(target=auth2fa, args=(account, passwd, key))
            th.start()
            resw = await auth2faWait(key=key, msg=msg)  # 随后主执行流来这里等待
            res_auth = await resw['auth'].get_RiotAuth()  # 直接获取RiotAuth对象
            is2fa = resw['auth'].is2fa # 是否是2fa用户
            # 4.如果没有抛出异常，那就是完成登录了，设置用户的玩家uuid+昵称
            UserTokenDict[msg.author.id] = {
                'auth_user_id': res_auth.user_id, 
                'GameName': resw['auth'].Name, 
                'TagLine': resw['auth'].Tag
            }
            UserAuthDict[msg.author.id] = {"auth": res_auth, "2fa": is2fa } # 将对象插入
            # 设置基础打印信息
            text = f"登陆成功！欢迎回来，{UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            info_text = "当前cookie有效期为2~3天，随后您需要重启登录"

            # 5.发送登录成功的信息
            await msg.reply(content=f"{text}\n{info_text}")

            # 6.全部都搞定了，打印登录信息日志
            _log.info(
                f"[Login] Au:{msg.author.id} - {UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            )
        except EzAuthExp.AuthenticationError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}")
            await msg.reply(content=f"登录错误，请检查账户、密码、邮箱验证码")
        except EzAuthExp.WaitOvertimeError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}")
            await msg.reply(content="2fa等待超时，会话关闭")
        except EzAuthExp.RatelimitError as result:
            err_str = f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}"
            # 更新全局速率限制
            login_rate_limit = {'limit': True, 'time': time.time()}
            _log.info(err_str," set login_rate_limit = True")
            # 这里是第一个出现速率限制err的用户,更新消息提示
            await msg.reply(content=f"登录请求超速！请在{RATE_LIMITED_TIME}s后重试")
        except KeyError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - KeyError:{result}")
            text = f"遇到未知的KeyError，请联系阿狸的主人哦~"
            if '0' in str(result):
                text = f"遇到不常见的KeyError，可能👊Api服务器炸了"
            # 发送信息
            await msg.reply(content=text)
        except client_exceptions.ClientResponseError as result:
            err_str = f"ERR! [{GetTime()}] login Au:{msg.author_id}\n```\n{traceback.format_exc()}\n```\n"
            if 'auth.riotgames.com' and '403' in str(result):
                Login_Forbidden = True
                err_str += f"[Login] 403 err! set Login_Forbidden = True"
            elif '404' in str(result):
                err_str += f"[Login] 404 err! network err, try again"
            else:
                err_str += f"[Login] Unkown aiohttp ERR!"
            # 打印+发送消息
            _log.info(err_str)
            await msg.reply(content=f"出现了aiohttp请求错误！获取失败，请稍后重试")
        except Exception as result:
            text=f"ERR! [{GetTime()}] login Au:{msg.author.id}\n{traceback.format_exc()}"
            _log.info(text)
            await msg.reply(content=f"出现了未知错误！login\n{result}")
    

    # 邮箱验证
    async def tfa_cmd(self,msg:Message,vcode:str):
        _log.info(f"[tfa] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")
        try:
            global User2faCode
            key = msg.author.id
            if key in User2faCode:
                User2faCode[key]['vcode'] = vcode
                User2faCode[key]['2fa_status']=True
                await msg.reply(content=f"邮箱验证码「{vcode}」获取成功，请等待...")
            else:
                await msg.reply(content=f"您尚未登录，请先执行「/login 账户 密码」")
        except Exception as result:
            text=f"ERR! [{GetTime()}] tfa Au:{msg.author.id}\n{traceback.format_exc()}"
            _log.info(text)
            await msg.reply(content=f"出现错误！tfa\n{result}")
    
    # 帮助命令
    async def help_cmd(self, msg: Message):
        text = help_text(self.robot.id)
        await msg.reply(content=text)
        _log.info(f"[help] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")

    # 获取商店
    async def shop_cmd(self,msg:Message):
        _log.info(f"[shop] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        if msg.author.id not in UserAuthDict:
            await msg.reply(content=f"您尚未登录，请私聊使用「/login 账户 密码」登录")
            return
        try:
            # 1.判断是否需要重新reauth
            reau = await check_reauth("每日商店", msg)
            if reau == False: return  # 如果为假说明重新登录失败，直接退出
            
            # 2.重新获取token成功，从dict中获取玩家昵称
            player_gamename = f"{UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            # 2.1 提示正在获取商店
            await msg.reply(content=f"正在获取玩家「{player_gamename}」的每日商店")

            # 2.2 计算获取每日商店要多久
            start_time = time.perf_counter()  #开始计时
            # 2.3 从auth的dict中获取RiotAuth对象
            auth = UserAuthDict[msg.author.id]['auth']
            userdict = {
                'auth_user_id': auth.user_id,
                'access_token': auth.access_token,
                'entitlements_token': auth.entitlements_token
            }
            log_time = ""
            shop_api_time = time.time() # api调用计时
            # 3.api获取每日商店
            resp = await fetch_daily_shop(userdict)  
            list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
            timeout = resp["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]  # 剩余时间
            timeout = time.strftime("%H:%M:%S", time.gmtime(timeout))  # 将秒数转为标准时间
            log_time += f"[Api.shop] {format(time.time()-shop_api_time,'.4f')} "
            # 4.api获取用户vp/rp
            vrDict = await fetch_vp_rp_dict(userdict)
            # 5.请求shop-draw接口，获取返回值
            draw_time = time.time() # 开始画图计时
            ret = await shop_draw_get(list_shop=list_shop,vp=vrDict['vp'],rp=vrDict['rp'])
            if ret['code']: # 出现错误
                raise Exception(f"shop-draw err! {ret}")
            # 返回成功
            log_time += f"- [Drawing] {format(time.time() - draw_time,'.4f')} - [Au] {msg.author.id}"
            _log.info(log_time)
            # 6.一切正常，获取图片bytes 
            # https://bot.q.qq.com/wiki/develop/gosdk/api/message/message_format.html#message
            # 发现可以直接传图片url，但是sdk的exp里面没有，看来还是得自己看文档
            _log.info(f"[imgUrl] {ret['message']}")
            # img_bytes= await shop_img_load(ret['message'],key=msg.author.id)
            # 7.发送图片
            shop_using_time = format(time.perf_counter() - start_time, '.2f') # 结束总计时
            await msg.reply(
                content=f"玩家「{player_gamename}」的商店\n本次查询耗时：{shop_using_time}s",
                image=ret['message']
            )
            # 8.结束，打印
            _log.info(
                f"[{GetTime()}] Au:{msg.author.id} daily_shop reply success [{shop_using_time}]"
            )
        except Exception as result:
            err_str = f"[{GetTime()}] shop Au:{msg.author.id}\n{traceback.format_exc()}"
            if "SkinsPanelLayout" in str(result):
                _log.info(err_str, resp)
                btext = f"KeyError:{result}, please re-login\n如果此问题重复出现，请联系开发者"
                await msg.reply(content=f"出现键值错误\n{btext}")
            if "upload image error" in str(result):
                _log.info(err_str)
                await msg.reply(content=f"[shop] 出现图片上传错误！这是常见错误，重试即可\n{result}")
            else:
                _log.info(err_str)
                await msg.reply(content=f"[shop] 出现未知错误！\n{result}")
            

    # 获取uinfo
    async def uinfo_cmd(self,msg:Message):
        text ="当前玩家资产信息\n"
        text+="vp: 1032\n"
        text+="rp: 232\n"
        text+="玩家等级: 3\n"
        await msg.reply(content=text)
        return

    # 监听公频消息
    async def on_at_message_create(self, message: Message):
        try:
            # 检测配置，设置某个服务器的特定频道才能使用bot（需要修改配置文件)
            if not listenConf.isActivate(gid=message.guild_id,chid=message.channel_id):
                return
            # 检测通过，执行
            content = message.content
            if '/ahri' in content or '/help' in content:
                await self.help_cmd(message)
            elif '/login' in content or '/tfa' in content:
                await message.reply(content=f"为了您的隐私，「/login」和「/tfa」命令仅私聊可用！\nPC端无bot私聊入口，请先在手机端上私聊bot，便可在PC端私聊")
            elif '/shop' in content or '/store' in content:
                await self.shop_cmd(message)
            elif '/uinfo' in content:
                await self.uinfo_cmd(message)
            elif '/pm' in content:
                text = f"收到pm命令，「{self.robot.name}」给您发起了私信"
                await message.reply(content=text)
                ret_dms = await self.api.create_dms(message.guild_id,message.author.id)
                await self.api.post_dms(guild_id=ret_dms['guild_id'],content=text)
            else:
                return
        except Exception as result:
            _log.info(traceback.format_exc())
            await message.reply(f"[on_at_message_create]\n出现了未知错误，请联系开发者！\n{result}")

    # 监听私聊消息
    async def on_direct_message_create(self, message: DirectMessage):
        try:
            content = message.content
            if '/ahri' in content or '/help' in content:
                await self.help_cmd(message)
            if '/login' in content:
                # /login 账户 密码
                first = content.find(' ') #第一个空格
                second = content.rfind(' ')#第二个空格
                await self.login_cmd(message,account=content[first+1:second],passwd=content[second+1:])
            elif '/tfa' in content:
                # /tfa vcode
                first = content.rfind(' ') #第一个空格
                await self.tfa_cmd(message,vcode=content[first+1:])
            elif '/shop' in content or '/store' in content:
                await self.shop_cmd(message)
            elif '/uinfo' in content:
                await self.uinfo_cmd(message)
            elif '/kill' in content:
                # 只有作者能操作此命令
                if message.author.id == bot_config['master_id']:
                    save_all_file() # 保存所有文件
                    await message.reply(content=f"「{self.robot.name}」准备退出")
                    _log.info(f"[BOT.KILL] bot off at {GetTime()}\n")
                    os._exit(0)
            else:
                return
        except Exception as result:
            _log.info(traceback.format_exc())
            await message.reply(f"[on_direct_message_create]\n出现了未知错误，请联系开发者！\n{result}")


# 保存所有文件的task
def save_file_task():
    while True:
        save_all_file()
        time.sleep(300)#执行一次，睡5分钟

if __name__ == "__main__":
    # 通过kwargs，设置需要监听的事件通道
    _log.info(f"[BOT.START] start at {GetTime()}")
    # 实现一个保存所有文件的task（死循环
    threading.Thread(target=save_file_task).start()
    _log.info(f"[BOT.START] save_all_file task start {GetTime()}")
    # 运行bot
    intents = botpy.Intents(public_guild_messages=True,direct_message=True)
    client = MyClient(intents=intents)
    client.run(appid=bot_config["appid"], token=bot_config["token"])
