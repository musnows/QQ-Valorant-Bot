# -*- coding: utf-8 -*-
import time
import threading
import traceback
import os

import botpy
from aiohttp import client_exceptions
from apscheduler.schedulers.background import BackgroundScheduler

from botpy import errors
from botpy.message import Message,DirectMessage
from botpy.types.message import Reference
from utils.FileManage import bot_config,UserTokenDict,UserAuthDict,UserApLog,save_all_file,_log,SkinRateDict,UserRtsDict
from utils.valorant import Val,ShopApi,ShopRate
from utils.valorant.EzAuth import EzAuthExp,auth2faWait,auth2fa,authflow,User2faCode
from utils import BotVip
from utils.Gtime import GetTime
from utils.Channel import listenConf
from utils.Proc import get_proc_info

# help命令文字
def help_text(bot_id:str):
    text = "以下为阿狸的的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+= "「/shop」查询商店\n"
    text+= "「/uinfo」查询用户vp/rp/等级\n"
    text+= "「/rate 皮肤名」查找皮肤，选择指定皮肤进行打分\n"
    text+= "「/rts 序号 打分 吐槽」选中皮肤序号，给该皮肤打个分(0~100) 再吐槽一下!\n"
    text+= "「/kkn」查看昨日评分最高/最低的用户\n"
    text+=f"在公频中使用命令，需要在命令前加上 <@{bot_id}>\n"
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
        at_text = f"<@{user_id}>\n"
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
            text = f"{at_text}获取「{def_name}」失败！正在尝试重新获取token，您无需操作"
            await msg.reply(content=f"{text}\n{resp['message']}")
        # 不管传入的是用户id还是msg，都传user_id进入该函数
        ret = await login_reauth(user_id)
        if ret == False and is_msg:  #没有正常返回,重新获取token失败
            text = f"{at_text}重新获取token失败，请私聊「/login」重新登录\n"
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
        if is_msg: msg.reply(f"{at_text}出现错误！check_reauth:\naiohttp client_exceptions ClientResponseError")
        _log.info(err_str)
        return False
    except Exception as result:
        if 'httpStatus' in str(result):
            _log.info(f"[Check reauth] Au:{user_id} No need to reauthorize [{result}]")
            return True
        else:
            if is_msg: msg.reply(f"{at_text}出现错误！check_reauth:\n{result}")
            _log.info(f"[Check reauth] Unkown ERR!\n{traceback.format_exc()}")
            return False

# bot main
class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")


    # 登录命令
    async def login_cmd(self,msg:Message,account:str,passwd:str,at_text):
        _log.info(f"[login] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")
        global UserAuthDict,UserTokenDict,Login_Forbidden
        try:
            # 1.检查全局登录速率
            if not Val.loginStat.checkRate(): return
            # 2.发送开始登录的提示消息
            await msg.reply(content=f"正在获取您的账户token和cookie",message_reference=at_text)

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
            info_text = "当前cookie有效期为2~3天，随后您需要重新登录"

            # 5.发送登录成功的信息
            await msg.reply(content=f"{text}\n{info_text}",message_reference=at_text)

            # 5.1 用于保存cookie的路径, 保存用户登录信息
            if await BotVip.is_vip(msg.author.id):
                cookie_path = f"./log/cookie/{msg.author.id}.cke"
                res_auth._cookie_jar.save(cookie_path)  # 保存

            # 6.全部都搞定了，打印登录信息日志
            _log.info(
                f"[Login] Au:{msg.author.id} - {UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            )
        except EzAuthExp.AuthenticationError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}")
            await msg.reply(content=f"登录错误，请检查账户、密码、邮箱验证码",message_reference=at_text)
        except EzAuthExp.WaitOvertimeError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}")
            await msg.reply(content="2fa等待超时，会话关闭",message_reference=at_text)
        except EzAuthExp.RatelimitError as result:
            err_str = f"ERR! [{GetTime()}] login Au:{msg.author.id} - {result}"
            # 更新全局速率限制
            Val.loginStat.setRateLimit()
            # 这里是第一个出现速率限制err的用户,更新消息提示
            await msg.reply(content=f"登录请求超速！请在{Val.loginStat.RATE_LIMITED_TIME}s后重试",message_reference=at_text)
            _log.info(err_str," set login_rate_limit = True")
        except KeyError as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id} - KeyError:{result}")
            text = f"遇到未知的KeyError，请联系阿狸的主人哦~"
            if '0' in str(result):
                text = f"遇到不常见的KeyError，可能👊Api服务器炸了"
            # 发送信息
            await msg.reply(content=text,message_reference=at_text)
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
            await msg.reply(content=f"出现了aiohttp请求错误！获取失败，请稍后重试",message_reference=at_text)
        except Exception as result:
            text=f"ERR! [{GetTime()}] login Au:{msg.author.id}\n{traceback.format_exc()}"
            _log.info(text)
            await msg.reply(content=f"出现了未知错误！login\n{result}",message_reference=at_text)


    # 邮箱验证
    async def tfa_cmd(self,msg:Message,vcode:str,at_text):
        _log.info(f"[tfa] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")
        try:
            global User2faCode
            key = msg.author.id
            if key in User2faCode:
                User2faCode[key]['vcode'] = vcode
                User2faCode[key]['2fa_status']=True
                await msg.reply(content=f"邮箱验证码「{vcode}」获取成功，请等待...",message_reference=at_text)
            else:
                await msg.reply(content=f"您尚未登录，请先执行「/login 账户 密码」",message_reference=at_text)
        except Exception as result:
            text=f"ERR! [{GetTime()}] tfa Au:{msg.author.id}\n{traceback.format_exc()}"
            _log.info(text)
            await msg.reply(content=f"出现错误！tfa\n{result}",message_reference=at_text)

    # 帮助命令
    async def help_cmd(self, msg: Message,at_text):
        text = help_text(self.robot.id)
        await msg.reply(content=text,message_reference=at_text)
        _log.info(f"[help] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")

    # 获取商店
    async def shop_cmd(self,msg:Message,at_text):
        _log.info(f"[shop] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        if msg.author.id not in UserAuthDict:
            await msg.reply(content=f"您尚未登录，请私聊使用「/login 账户 密码」登录",message_reference=at_text)
            return
        try:
            # 1.判断是否需要重新reauth
            reau = await check_reauth("每日商店", msg)
            if reau == False: return  # 如果为假说明重新登录失败，直接退出

            # 2.重新获取token成功，从dict中获取玩家昵称
            player_gamename = f"{UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']}"
            # 2.1 提示正在获取商店
            await msg.reply(content=f"正在获取玩家「{player_gamename}」的每日商店",message_reference=at_text)

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
            # vrDict = await Val.fetch_vp_rp_dict(userdict)
            # 5.请求shop-draw接口，获取返回值
            draw_time = time.time() # 开始画图计时
            ret = await ShopApi.shop_draw_get(list_shop=list_shop,img_ratio="1")
            if ret['code']: # 出现错误
                raise Exception(f"shop-draw err! {ret}")
            # 返回成功
            log_time += f"- [Drawing] {format(time.time() - draw_time,'.4f')} - [Au] {msg.author.id}"
            _log.info(log_time)
            # 6.一切正常，获取图片bytes (跳过，采用url传图)
            # https://bot.q.qq.com/wiki/develop/gosdk/api/message/message_format.html#message
            # 发现可以直接传图片url，但是sdk的exp里面没有，看来还是得自己看文档
            _log.info(f"[imgUrl] {ret['message']}")
            # img_bytes= await shop_img_load(ret['message'],key=msg.author.id)

            # 7.皮肤评分和评价
            cm = await ShopRate.get_shop_rate_cm(list_shop, msg.author.id)
            # 死循环尝试上传
            i = 0 # 尝试次数
            while True:
                try:
                    i+=1 # 尝试次数+1
                    shop_using_time = format(time.perf_counter() - start_time, '.2f')  # 结束总计时
                    await msg.reply(
                        content=f"<@{msg.author.id}>\n玩家「{player_gamename}」的商店\n本次查询耗时：{shop_using_time}s\n\n{cm}",
                        image=ret['message']
                    )
                    break # 走到这里代表reply成功
                except errors.ServerError as result:
                    # 出现上传图片错误
                    if "download file err" in str(result) or "upload image error" in str(result):
                        if i >= 4: # 尝试超过4次了
                            raise result # 跳出循环
                        # 打印错误信息
                        _log.info(f"[{i}] Au:{msg.author.id} = botpy.errors.ServerError: {result}") 
                        continue # 重试
                    else:# 其他错误，依旧raise
                        raise result
            
            # 结束，打印信息
            _log.info(
                f"[{GetTime()}] Au:{msg.author.id} daily_shop reply success [{shop_using_time}]"
            )
        except Exception as result:
            err_str = f"[{GetTime()}] shop Au:{msg.author.id}\n{traceback.format_exc()}"
            if "SkinsPanelLayout" in str(result):
                _log.info(err_str, resp)
                btext = f"KeyError:{result}, please re-login\n如果此问题重复出现，请联系开发者"
                await msg.reply(content=f"[shop] 出现键值错误\n{btext}",message_reference=at_text)
            if "download file err" in str(result) or "upload image error" in str(result):
                _log.info(err_str)
                await msg.reply(content=f"[shop] 出现图片上传错误！这是常见错误，重试即可\n{result}",message_reference=at_text)
            else:
                _log.info(err_str)
                await msg.reply(content=f"[shop] 出现未知错误！\n{result}",message_reference=at_text)


    # 获取uinfo
    async def uinfo_cmd(self,msg:Message,at_text=""):
        _log.info(f"[uinfo] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        if msg.author.id not in UserAuthDict:
            await msg.reply(content=f"您尚未登录，请私聊使用「/login 账户 密码」登录",message_reference=at_text)
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
                await msg.reply(content=f"拳头api返回值错误，您是否登录了一个全新的账户？",message_reference=at_text)
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
            text =f"玩家 {UserTokenDict[msg.author.id]['GameName']}#{UserTokenDict[msg.author.id]['TagLine']} 的个人信息\n"
            text+= f"玩家称号：" + player_title['data']['displayName'] + "\n"
            text+= f"玩家等级：{player_level}  |  经验值：{player_level_xp}\n"
            text+= f"上次首胜：{last_fwin}\n"
            text+= f"首胜重置：{next_fwin}\n"
            text+= f"rp：{resp['rp']}  |  vp：{resp['vp']}"
            # 5.发送消息
            await msg.reply(content=f"<@{msg.author.id}>\n"+text,image=player_card['data']['wideArt'])
            _log.info(f"[{GetTime()}] Au:{msg.author.id} uinfo reply successful!")
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] uinfo\n{traceback.format_exc()}")
            if "Identity" in str(result) or "Balances" in str(result):
                await msg.reply(content=f"[uinfo] 键值错误，请重新登录\n{result}",message_reference=at_text)
            elif "download file err" in str(result)  or "upload image error"  in str(result):
                await msg.reply(content=f"<@{msg.author.id}>\n{text}\n获取玩家卡面图片错误",message_reference=at_text)
            else:
                await msg.reply(content=f"[uinfo] 未知错误\n{result}",message_reference=at_text)
    
    # 获取昨日最高/最低
    async def kkn_cmd(self,msg:Message,at_text):
        _log.info(f"[kkn] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        try:
            # 从数据库中获取
            cmpRet = await ShopRate.get_ShopCmp()
            if not cmpRet['status']:
                await msg.reply(content=f"获取昨日天选之子和丐帮帮主出错！请重试或联系开发者",message_reference=at_text)
                return
            
            # best
            text = f"天选之子 综合评分 {cmpRet['best']['rating']}"
            text+= f", 来自{cmpRet['best']['platform']}\n"
            for sk in cmpRet['best']['skin_list']:
                # 数据库中获取一个皮肤的评分情况
                skinRet = await ShopRate.query_SkinRate(sk)
                if skinRet['status']:
                    skin_name = f"「{skinRet['skin_name']}」"
                    text += f"%-45s\t\t评分: {skinRet['rating']}\n" % skin_name
            # worse
            text+="\n"
            text+=f"丐帮帮主 综合评分 {cmpRet['worse']['rating']}"
            text+=f", 来自{cmpRet['worse']['platform']}\n"
            for sk in cmpRet['worse']['skin_list']:
                # 数据库中获取一个皮肤的评分情况
                skinRet = await ShopRate.query_SkinRate(sk)
                if skinRet['status']:
                    skin_name = f"「{skinRet['skin_name']}」"
                    text += f"%-45s\t\t评分: {skinRet['rating']}\n" % skin_name

            await msg.reply(content=text,message_reference=at_text)
            _log.info(f"[{GetTime()}] [kkn] reply success")
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] kkn\n{traceback.format_exc()}")
            await msg.reply(content=f"[kkn] 出现错误\n{result}",message_reference=at_text)
    
    # 选择需要评论的皮肤
    async def rate_cmd(self,msg:Message,name:str,at_text):
        _log.info(f"[rate] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        try:
            retlist = await ShopRate.get_available_skinlist(name)
            if retlist == []:  # 空list，有问题
                await msg.reply(content=f"该皮肤不在列表中[或没有价格]，请重新查询！",message_reference=at_text)
                return

            # 将皮肤list插入到选择列表中，用户使用/rts命令选择
            UserRtsDict[msg.author.id] = retlist
            # 获取选择列表的text
            ret = await ShopRate.get_skinlist_rate_text(retlist,msg.author.id)
            text = f"===========\n{ret['text']}===========\n"
            head = f"查询到 {name} 相关皮肤如下\n"
            sub_text = "请使用以下命令对皮肤进行评分;\n√代表您已评价过该皮肤，+已有玩家评价，-无人评价\n"
            # 操作介绍
            text1 =  "===========\n"
            text1 += "「/rts 序号 评分 吐槽」\n"
            text1 += "序号：上面列表中的皮肤序号\n"
            text1 += "评分：给皮肤打分，范围0~100\n"
            text1 += "吐槽：说说你对这个皮肤的看法\n"
            text1 += "吐槽的时候请注意文明用语！\n"
            text1 += "===========\n"
            text1 += f"您已经评价过了 {ret['sum']} 个皮肤"
            # 发送
            await msg.reply(content=head+text+sub_text+text1,message_reference=at_text)
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] rate\n{traceback.format_exc()}")
            await msg.reply(content=f"[rate] 出现错误\n{result}",message_reference=at_text)  

    # 评论皮肤
    async def rts_cmd(self,msg:Message,index:int,rating:int,comment:str,at_text):
        _log.info(f"[rts] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id} = {msg.content}")
        try:
            if msg.author.id not in UserRtsDict:
                await msg.reply(content=f"您需要执行 `/rate 皮肤名` 来查找皮肤\n再使用 `/rts` 进行选择",message_reference=at_text)
                return

            _index = int(index)  #转成int下标（不能处理负数）
            _rating = int(rating)  #转成分数
            if _index >= len(UserRtsDict[msg.author.id]):  #下标判断，避免越界
                await msg.reply(f"您的选择越界了！请正确填写序号")
                return
            elif _rating < 0 or _rating > 100:
                await msg.reply(f"您的评分有误，正确范围为0~100")
                return

            S_skin = UserRtsDict[msg.author.id][_index]
            skin_uuid = S_skin['skin']['lv_uuid']
            point = _rating
            text1 = ""
            text2 = ""
            # 先从leancloud获取该皮肤的分数
            skin_rate = await ShopRate.query_SkinRate(skin_uuid)
            if skin_rate['status']: # 找到了
                #用户的评分和皮肤平均分差值不能超过32，避免有人乱刷分
                if abs(float(_rating) - skin_rate['rating']) <= 32:
                    # 计算分数
                    point = (skin_rate['rating'] + float(_rating)) / 2
                else:  # 差值过大，不计入皮肤平均值
                    point = skin_rate['rating']
                    text2 += f"由于您的评分和皮肤平均分差值大于32，所以您的评分不会计入皮肤平均分，但您的评论会进行保留\n"

            # 更新数据库中皮肤评分
            await ShopRate.update_SkinRate(skin_uuid,S_skin['skin']['displayName'],point)
            # 用户之前没有评价过，新建键值
            if msg.author.id not in SkinRateDict['data']:
                SkinRateDict['data'][msg.author.id] = {}
            # 设置uuid的键值
            SkinRateDict['data'][msg.author.id][skin_uuid] = {}
            SkinRateDict['data'][msg.author.id][skin_uuid]['name'] = S_skin['skin']['displayName']
            SkinRateDict['data'][msg.author.id][skin_uuid]['cmt'] = comment
            SkinRateDict['data'][msg.author.id][skin_uuid]['pit'] = point
            SkinRateDict['data'][msg.author.id][skin_uuid]['time'] = int(time.time()) # 秒级
            SkinRateDict['data'][msg.author.id][skin_uuid]['msg_id'] = msg.id
            # 数据库添加该评论
            await ShopRate.update_UserRate(skin_uuid,SkinRateDict['data'][msg.author.id][skin_uuid],msg.author.id)
            # 更新用户已评价的皮肤
            await ShopRate.update_UserCmt(msg.author.id,skin_uuid)

            text1 += f"评价成功！{S_skin['skin']['displayName']}"
            text2 += f"您的评分：{_rating}\n"
            text2 += f"皮肤平均分：{point}\n"
            text2 += f"您的评语：{comment}"
            # 设置成功并删除list后，再发送提醒事项设置成功的消息
            await msg.reply(content=text1+"\n"+text2,message_reference=at_text)
            _log.info(f"[{GetTime()}] [rts] Au:{msg.author.id} {text1} {skin_uuid}")    
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] rts\n{traceback.format_exc()}")
            await msg.reply(content=f"[rts] 出现错误\n{result}",message_reference=at_text)

    # 监听公频消息
    async def on_at_message_create(self, message: Message):
        try:
            # 构造消息发送请求数据对象
            at_text = Reference(message_id=message.id)
            # 检测配置，设置某个服务器的特定频道才能使用bot（需要修改配置文件)
            if not listenConf.isActivate(gid=message.guild_id,chid=message.channel_id):
                chlist = listenConf.activateCh(gid=message.guild_id)
                text = f"当前频道配置了命令专用子频道，请在专用子频道中使用机器人\n"
                for ch in chlist:
                    text+=f"<#{ch}> "
                await message.reply(content=text,message_reference=at_text)
                _log.info(f"[listenConf] abort cmd = G:{message.guild_id} C:{message.channel_id} Au:{message.author.id}")
                return
            # 检测通过，执行
            content = message.content
            # 用于发起私信（解除3条私信限制）
            if '/pm' in content:
                text = f"收到pm命令，「{self.robot.name}」给您发起了私信"
                await message.reply(content=text,message_reference=at_text)
                ret_dms = await self.api.create_dms(message.guild_id,message.author.id)
                await self.api.post_dms(guild_id=ret_dms['guild_id'],content=text)
            elif '/ahri' in content or '/help' in content:
                await self.help_cmd(message,at_text)
            elif '/kkn' in content:
                await self.kkn_cmd(msg=message,at_text=at_text)
            elif '/rate' in content:
                # /rate 皮肤名字
                if len(content) < 6: # /rate加一个空格 至少会有6个字符
                    await message.reply(content=f"参数长度不足，请提供皮肤名\n栗子「/rate 皮肤名字」")
                    return
                # 正常，分离参数
                content = content[content.find("/rate"):] # 把命令之前的内容给去掉
                first = content.find(' ') #第一个空格
                await self.rate_cmd(message,name=content[first+1:],at_text=at_text)
            elif '/rts' in content:
                # /rts 编号 分数 评论
                if len(content) < 7: # /rts加3个空格 至少会有7个字符
                    await message.reply(content=f"参数长度不足，请检查您的参数\n栗子「/rts 编号 分数 评论」")
                    return
                # 把命令之前的内容给去掉
                content = content[content.find("/rts"):]
                first = content.find(' ') #第1个空格
                second = content.find(' ',first+1)#第2个空格
                third = content.rfind(' ')#第3个空格
                await self.rts_cmd(message,index=int(content[first+1:second]),rating=int(content[second+1:third]),comment=content[third+1:],at_text=at_text)
            # 判断是否出现了速率超速或403错误
            elif Val.loginStat.Bool():
                if '/login' in content or '/tfa' in content:
                    await message.reply(content=f"为了您的隐私，「/login」和「/tfa」命令仅私聊可用！\nPC端无bot私聊入口，请先在手机端上私聊bot，便可在PC端私聊\n使用方法详见/help命令",message_reference=at_text)
                elif '/shop' in content or '/store' in content:
                    await self.shop_cmd(message,at_text)
                elif '/uinfo' in content:
                    await self.uinfo_cmd(message,at_text)
            else: # 无法执行登录
                await Val.loginStat.sendForbidden(msg=Message)
                _log.info(f"[LoginStatus] Au:{message.author.id} Command Failed")
                return
        except Exception as result:
            _log.info(f"[at_msg] G:{message.guild_id} C:{message.channel_id} Au:{message.author.id} = {message.content}")
            _log.info(traceback.format_exc())
            await message.reply(content=f"[on_at_message_create]\n出现了未知错误，请联系开发者！\n{result}",message_reference=at_text)

    # 监听私聊消息
    async def on_direct_message_create(self, message: DirectMessage):
        try:
            content = message.content
            # 构造消息发送请求数据对象
            at_text = Reference(message_id=message.id)
            if '/ahri' in content or '/help' in content:
                await self.help_cmd(message,at_text)
            # 只有作者能操作此命令
            elif '/kill' in content and (message.author.id == bot_config['master_id']):
                save_all_file() # 保存所有文件
                await message.reply(content=f"「{self.robot.name}」准备退出",message_reference=at_text)
                _log.info(f"[BOT.KILL] bot off at {GetTime()}\n")
                os._exit(0)
            elif '/mem' in content and (message.author.id == bot_config['master_id']):
                text = await get_proc_info()
                await message.reply(content=text,message_reference=at_text)
            elif '/kkn' in content:
                await self.kkn_cmd(msg=message,at_text=at_text)
            elif '/rate' in content:
                # /rate 皮肤名字
                if len(content) < 6: # /rate加一个空格 至少会有6个字符
                    await message.reply(content=f"参数长度不足，请提供皮肤名\n栗子「/rate 皮肤名字」")
                    return
                # 正常，分离参数
                content = content[content.find("/rate"):] # 把命令之前的内容给去掉
                first = content.find(' ') #第一个空格
                await self.rate_cmd(message,name=content[first+1:],at_text=at_text)
            elif '/rts' in content:
                # /rts 编号 分数 评论
                if len(content) < 7: # /rts加3个空格 至少会有7个字符
                    await message.reply(content=f"参数长度不足，请检查您的参数\n栗子「/rts 编号 分数 评论」")
                    return
                content = content[content.find("/rts"):] # 把命令之前的内容给去掉
                first = content.find(' ') #第1个空格
                second = content.find(' ',first+1)#第2个空格
                third = content.rfind(' ')#第3个空格
                await self.rts_cmd(message,index=int(content[first+1:second]),rating=int(content[second+1:third]),comment=content[third+1:],at_text=at_text)
            # 判断是否出现了速率超速或403错误
            elif Val.loginStat.Bool():
                if '/login' in content:
                    # /login 账户 密码
                    if len(content) < 8: # /login加两个空格 至少会有8个字符，少了有问题
                        await message.reply(content=f"参数长度不足，请提供账户/密码\b栗子「/login 账户 密码」")
                        return
                    # 正常，分离参数
                    content = content[content.find("/login"):] # 把命令之前的内容给去掉
                    first = content.find(' ') #第一个空格
                    second = content.rfind(' ')#第二个空格
                    await self.login_cmd(message,account=content[first+1:second],passwd=content[second+1:],at_text=at_text)
                elif '/tfa' in content:
                    # /tfa vcode
                    if len(content) < 5: # /tfa加一个空格 至少会有5个字符
                        await message.reply(content=f"参数长度不足，请提供邮箱验证码\n栗子「/tfa 114514」")
                        return
                    content = content[content.find("/tfa"):] # 把命令之前的内容给去掉
                    first = content.rfind(' ') #第一个空格
                    await self.tfa_cmd(message,vcode=content[first+1:],at_text=at_text)
                elif '/shop' in content or '/store' in content:
                    await self.shop_cmd(message,at_text=at_text)
                elif '/uinfo' in content:
                    await self.uinfo_cmd(message,at_text=at_text)
            else: # 无法登录
                await Val.loginStat.sendForbidden(message)
                _log.info(f"[LoginStatus] Au:{message.author.id} Command Failed")
                return
        except Exception as result:
            _log.info(f"[dm_msg] G:{message.guild_id} C:{message.channel_id} Au:{message.author.id} = {message.content}")
            _log.info(traceback.format_exc())
            await message.reply(content=f"[on_direct_message_create]\n出现了未知错误，请联系开发者！\n{result}",message_reference=at_text)


# 保存所有文件的task
def save_file_task():
    while True:
        save_all_file()
        time.sleep(300)#执行一次，睡5分钟

# 更新任务
import copy
def shop_cmp_post_task():
    # 清空已有数据
    SkinRateDict["kkn"] = copy.deepcopy(SkinRateDict["cmp"])
    SkinRateDict["cmp"]["best"]["list_shop"] = list()
    SkinRateDict["cmp"]["best"]["rating"] = 0
    SkinRateDict["cmp"]["worse"]["list_shop"] = list()
    SkinRateDict["cmp"]["worse"]["rating"] = 100
    # 更新到db
    ret = ShopApi.shop_cmp_post(SkinRateDict["kkn"]["best"],SkinRateDict["kkn"]["worse"])
    _log.info(f"[ShopCmp.TASK] {ret.json()}")

# 更新商店比较的task
def update_ShopCmt_task():
    # 创建调度器BackgroundScheduler，不会阻塞线程
    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
    # 在每天早上8点1分执行
    scheduler.add_job(shop_cmp_post_task, 'cron',hour='8',minute='1',id='update_ShopCmt_task')
    scheduler.start()

if __name__ == "__main__":
    # 通过kwargs，设置需要监听的事件通道
    _log.info(f"[BOT.START] start at {GetTime()}")
    # 实现一个保存所有文件的task（死循环
    threading.Thread(target=save_file_task).start()
    _log.info(f"[BOT.START] save_all_file task start {GetTime()}")
    update_ShopCmt_task() # 早八商店评价更新
    _log.info(f"[BOT.START] update_ShopCmt task start {GetTime()}")
    # 运行bot
    intents = botpy.Intents(public_guild_messages=True,direct_message=True)
    client = MyClient(intents=intents)
    client.run(appid=bot_config["appid"], token=bot_config["token"])
