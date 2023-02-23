# -*- coding: utf-8 -*-
import time
import threading
import traceback
import os

import botpy
from aiohttp import client_exceptions

from botpy.message import Message,DirectMessage
from utils.FileManage import bot_config,UserTokenDict,UserAuthDict,UserApLog,save_all_file,_log
from utils.valorant import Val,ShopApi
from utils.valorant.EzAuth import EzAuthExp,auth2faWait,auth2fa,authflow,User2faCode
from utils.Gtime import GetTime
from utils.Channel import listenConf
from utils.Proc import get_proc_info

# help命令文字
def help_text(bot_id:str):
    text = "以下为阿狸的的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+=f"「<@{bot_id}> /shop」查询商店\n"
    text+=f"「<@{bot_id}> /uinfo」查询用户vp/rp/等级\n"
    text+=f"机器人帮助频道，可在机器人介绍中点击加入！"
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
        _log.info(f"[Check reauth] Au:{user_id}")
        # 找键值，获取auth对象
        auth = UserAuthDict[user_id]['auth']
        userdict = {
            'auth_user_id': auth.user_id,
            'access_token': auth.access_token,
            'entitlements_token': auth.entitlements_token
        }
        # 调用riot api测试cookie是否过期
        resp = await Val.fetch_valorant_point(userdict)
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
        err_str = f"[Check reauth] aiohttp ERR!\n{traceback.format_exc()}"
        if 'auth.riotgames.com' and '403' in str(result):
            global Login_Forbidden
            Login_Forbidden = True
            err_str += f"[Check reauth] 403 err! set Login_Forbidden = True"
        elif '404' in str(result):
            err_str += f"[Check reauth] 404 err! network err, try again"
        else:
            err_str += f"[Check reauth] Unkown aiohttp ERR!"
        # 登陆失败
        if is_msg: msg.reply(f"出现错误！check_reauth:\naiohttp client_exceptions ClientResponseError")
        _log.info(err_str)
        return False
    except Exception as result:
        if 'httpStatus' in str(result):
            _log.info(f"[Check reauth] Au:{user_id} No need to reauthorize [{result}]")
            return True
        else:
            if is_msg: msg.reply(f"出现错误！check_reauth:\n{result}")
            _log.info(f"[Check reauth] Unkown ERR!\n{traceback.format_exc()}")
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
            if not Val.loginStat.checkRate(): return
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
            Val.loginStat.setRateLimit()
            # 这里是第一个出现速率限制err的用户,更新消息提示
            await msg.reply(content=f"登录请求超速！请在{Val.loginStat.RATE_LIMITED_TIME}s后重试")
            _log.info(err_str," set login_rate_limit = True")
        except KeyError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - KeyError:{result}")
            text = f"遇到未知的KeyError，请联系阿狸的主人哦~"
            if '0' in str(result):
                text = f"遇到不常见的KeyError，可能👊Api服务器炸了"
            # 发送信息
            await msg.reply(content=text)
        except client_exceptions.ClientResponseError as result:
            err_str = f"ERR! [{GetTime()}] login Au:{msg.author.id}\n```\n{traceback.format_exc()}\n```\n"
            if 'auth.riotgames.com' and '403' in str(result):
                Val.loginStat.setForbidden() # 设置forbidden
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
    async def help_cmd(self, msg: Message,at_text=""):
        text = help_text(self.robot.id)
        await msg.reply(content=at_text+text)
        _log.info(f"[help] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")

    # 获取商店
    async def shop_cmd(self,msg:Message,at_text=""):
        _log.info(f"[shop] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        if msg.author.id not in UserAuthDict:
            await msg.reply(content=f"{at_text}您尚未登录，请私聊使用「/login 账户 密码」登录")
            return
        try:
            # 1.判断是否需要重新reauth
            reau = await check_reauth("每日商店", msg)
            if reau == False: return  # 如果为假说明重新登录失败，直接退出
            
            # 2.重新获取token成功，从dict中获取玩家昵称
            player_gamename = f"{UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            # 2.1 提示正在获取商店
            await msg.reply(content=f"{at_text}正在获取玩家「{player_gamename}」的每日商店")

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
            resp = await Val.fetch_daily_shop(userdict)  
            list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
            timeout = resp["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]  # 剩余时间
            timeout = time.strftime("%H:%M:%S", time.gmtime(timeout))  # 将秒数转为标准时间
            log_time += f"[Api.shop] {format(time.time()-shop_api_time,'.4f')} "
            # 4.api获取用户vp/rp
            vrDict = await Val.fetch_vp_rp_dict(userdict)
            # 5.请求shop-draw接口，获取返回值
            draw_time = time.time() # 开始画图计时
            ret = await ShopApi.shop_draw_get(list_shop=list_shop,vp=vrDict['vp'],rp=vrDict['rp'])
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
                content=f"{at_text}玩家「{player_gamename}」的商店\n本次查询耗时：{shop_using_time}s",
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
    async def uinfo_cmd(self,msg:Message,at_text=""):
        _log.info(f"[uinfo] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        if msg.author.id not in UserAuthDict:
            await msg.reply(content=f"{at_text}您尚未登录，请私聊使用「/login 账户 密码」登录")
            return
        text=" "# 先设置为空串，避免except中报错
        try:
            # 1.检测是否需要重新登录
            reau = await check_reauth("uinfo", msg)  #重新登录
            if reau == False: return  #如果为假说明重新登录失败
            # 2.获取RiotAuth对象
            auth = UserAuthDict[msg.author.id]['auth']
            userdict = {
                'auth_user_id': auth.user_id,
                'access_token': auth.access_token,
                'entitlements_token': auth.entitlements_token
            }
            # 3.调用api，获取相关信息
            resp = await Val.fetch_player_loadout(userdict)  # 获取玩家装备栏
            player_card = await Val.fetch_playercard_uuid(resp['Identity']['PlayerCardID'])  # 玩家卡面id
            player_title = await Val.fetch_title_uuid(resp['Identity']['PlayerTitleID'])  # 玩家称号id
            # 3.1 检测返回值
            if 'data' not in player_card or player_card['status'] != 200:
                player_card = {'data': {'wideArt': 'https://img.kookapp.cn/assets/2022-09/PDlf7DcoUH0ck03k.png'}}
                _log.info(f"ERR![player_card]  Au:{msg.author.id} uuid:{resp['Identity']['PlayerCardID']}")
            if 'data' not in player_title or player_title['status'] != 200:
                player_title = {
                    'data': {
                        "displayName": f"未知玩家卡面uuid！\nUnknow uuid: `{resp['Identity']['PlayerTitleID']}`"
                    }
                }
                _log.info(f"ERR![player_title] Au:{msg.author.id} uuid:{resp['Identity']['PlayerTitleID']}")
            # 可能遇到全新账户（没打过游戏）的情况
            if resp['Guns'] == None or resp['Sprays'] == None:  
                await msg.reply(content=f"{at_text}拳头api返回值错误，您是否登录了一个全新的账户？")
                return

            # 3.2 获取玩家等级
            resp = await Val.fetch_player_level(userdict)
            player_level = resp["Progress"]["Level"]     # 玩家等级
            player_level_xp = resp["Progress"]["XP"]     # 玩家等级经验值
            last_fwin = resp["LastTimeGrantedFirstWin"]  # 上次首胜时间
            next_fwin = resp["NextTimeFirstWinAvailable"]# 下次首胜重置
            # 3.3 获取玩家的vp和r点剩余
            resp = await Val.fetch_vp_rp_dict(userdict)

            # 4.创建消息str
            text =f"{at_text}玩家 {UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']} 的个人信息\n"
            text+= f"玩家称号：" + player_title['data']['displayName'] + "\n"
            text+= f"玩家等级：{player_level}  |  经验值：{player_level_xp}\n"
            text+= f"上次首胜：{last_fwin}\n"
            text+= f"首胜重置：{next_fwin}\n"
            text+= f"rp：{resp['rp']}  |  vp：{resp['vp']}"
            # 5.发送消息
            await msg.reply(content=text,image=player_card['data']['wideArt'])
            _log.info(f"[{GetTime()}] Au:{msg.author.id} uinfo reply successful!")
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] uinfo\n{traceback.format_exc()}")
            if "Identity" in str(result) or "Balances" in str(result):
                await msg.reply(content=f"{at_text}[uinfo] 键值错误，请重新登录\n{result}")
            elif "download file err" in str(result):
                await msg.reply(content=f"{at_text}{text}\n获取玩家卡面图片错误")
            else:
                await msg.reply(content=f"{at_text}[uinfo] 未知错误\n{result}")

    # 监听公频消息
    async def on_at_message_create(self, message: Message):
        try:
            # 检测配置，设置某个服务器的特定频道才能使用bot（需要修改配置文件)
            if not listenConf.isActivate(gid=message.guild_id,chid=message.channel_id):
                chlist = listenConf.activateCh(gid=message.guild_id)
                text = f"<@{message.author.id}>\n当前频道配置了命令专用子频道，请在专用子频道中使用机器人\n"
                for ch in chlist:
                    text+=f"<#{ch}> "
                await message.reply(content=text)
                _log.info(f"[listenConf] abort cmd = G:{message.guild_id} C:{message.channel_id} Au:{message.author.id}")
                return
            # 检测通过，执行
            content = message.content
            at_text = f"<@{message.author.id}>\n"
            # 用于发起私信（解除3条私信限制）
            if '/pm' in content:
                text = f"<@{message.author.id}>\n收到pm命令，「{self.robot.name}」给您发起了私信"
                await message.reply(content=text)
                ret_dms = await self.api.create_dms(message.guild_id,message.author.id)
                await self.api.post_dms(guild_id=ret_dms['guild_id'],content=text)
            # 判断是否出现了速率超速或403错误
            elif Val.loginStat.Bool(): 
                if '/ahri' in content or '/help' in content:
                    await self.help_cmd(message,at_text)
                elif '/login' in content or '/tfa' in content:
                    await message.reply(content=f"<@{message.author.id}>\n为了您的隐私，「/login」和「/tfa」命令仅私聊可用！\nPC端无bot私聊入口，请先在手机端上私聊bot，便可在PC端私聊\n使用方法详见/help命令")
                elif '/shop' in content or '/store' in content:
                    await self.shop_cmd(message,at_text)
                elif '/uinfo' in content:
                    await self.uinfo_cmd(message,at_text)
            else: # 无法执行登录
                await Val.loginStat.sendForbidden(msg=Message)
                _log.info(f"[LoginStatus] Au:{message.author.id} Command Failed")
                return
        except Exception as result:
            _log.info(traceback.format_exc())
            await message.reply(f"<@{message.author.id}>\n[on_at_message_create]\n出现了未知错误，请联系开发者！\n{result}")

    # 监听私聊消息
    async def on_direct_message_create(self, message: DirectMessage):
        try:
            content = message.content
            if '/ahri' in content or '/help' in content:
                await self.help_cmd(message)
            # 只有作者能操作此命令
            elif '/kill' in content and (message.author.id == bot_config['master_id']):
                save_all_file() # 保存所有文件
                await message.reply(content=f"「{self.robot.name}」准备退出")
                _log.info(f"[BOT.KILL] bot off at {GetTime()}\n")
                os._exit(0)
            elif '/mem' in content and (message.author.id == bot_config['master_id']):
                text = await get_proc_info()
                await message.reply(content=text)
            # 判断是否出现了速率超速或403错误
            elif Val.loginStat.Bool():
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
            else: # 无法登录
                await Val.loginStat.sendForbidden(message)
                _log.info(f"[LoginStatus] Au:{message.author.id} Command Failed")
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
