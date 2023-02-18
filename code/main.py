# -*- coding: utf-8 -*-
import time
import threading
import traceback
import os

import botpy
from botpy import logging

from botpy.message import Message,DirectMessage
from botpy.types.message import MarkdownPayload, MessageMarkdownParams
from utils.FileManage import bot_config,UserTokenDict,UserAuthDict,save_all_file
from utils.valorant.ShopApi import *
from utils.valorant.EzAuth import EzAuth,EzAuthExp,Get2faWait_Key,auth2faWait,auth2fa
from utils.Gtime import GetTime

# 日志
_log = logging.get_logger()

# help命令文字
def help_text(bot_id:str):
    text = "以下为bot的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+=f"「<@{bot_id}> /shop」查询商店\n"
    text+=f"「<@{bot_id}> /uinfo」查询用户vp/rp/等级\n"
    return text

class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def handle_send_markdown_by_content(self, channel_id, msg_id):
        markdown = MarkdownPayload(content="# 标题 \n## 简介很开心 \n内容，测试")
        # 通过api发送回复消息
        await self.api.post_message(channel_id, markdown=markdown)

    # 私聊消息提醒
    async def msg_inform(self,msg:Message,text:str):
        await self.api.post_dms(
            guild_id=msg.guild_id,
            content=text,
            msg_id=msg.id,
        )
    
    # 登录命令
    async def login_cmd(self,msg:Message,account:str,passwd:str):
        global login_rate_limit
        try:
            # 1.检查全局登录速率
            await check_global_loginRate()  # 无须接收此函数返回值，直接raise
            # 2.发送开始登录的提示消息
            await msg.reply(content=f"正在获取您的账户token和cookie")

            # 3.登录，获取用户的token
            key = await Get2faWait_Key() # 先获取一个key
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
            await msg.reply(content=f"登录错误，请检查账户/密码/邮箱验证码")
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
        except Exception as result:
            _log.info(f"ERR! [{GetTime()}] login Au:{msg.author.id}\n{traceback.format_exc()}")
            text=f"出现了错误！\n{traceback.format_exc()}"
            await msg.reply(content=text)
    

    # 邮箱验证
    async def tfa_cmd(self,msg:Message,key:str,vcode:str):
        return
    
    # 帮助命令
    async def help_cmd(self, msg: Message):
        text = help_text(self.robot.id)
        await msg.reply(content=text)
        _log.info(f"[help] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")

    # 获取商店
    async def shop_cmd(self,msg:Message):
        img_bytes=None
        # 发送图片
        await self.api.post_dms(
            guild_id=msg.guild_id,
            content=f"成功获取您的商店！",
            msg_id=msg.id,
            file_image=img_bytes
        )
        return

    # 获取uinfo
    async def uinfo_cmd(self,msg:Message):
        return

    # 监听公频消息
    async def on_at_message_create(self, message: Message):
        #await self.handle_send_markdown_by_content(message.channel_id, message.id)
        content = message.content
        if '/ahri' in content or '/help' in content:
            await self.help_cmd(message)
        elif '/login' in content or '/tfa' in content:
            await message.reply(content=f"为了您的隐私，「/login」和「/tfa」命令仅私聊可用！")
        elif '/shop' in content:
            await self.shop_cmd(message)
        elif '/uinfo' in content:
            await self.uinfo_cmd(message)
        else:
            return

    # 监听私聊消息
    async def on_direct_message_create(self, message: DirectMessage):
        content = message.content
        if '/login' in content:
            # /login 账户 密码
            first = content.find(' ') #第一个空格
            second = content.rfind(' ')#第二个空格
            await self.login_cmd(message,account=content[first+1:second],passwd=content[second+1:])
        elif '/tfa' in content:
            await self.msg_inform(message,f"「{self.robot.name}」收到你的私信了！当前接口尚未完工！")
            # /tfa key vcode
            first = content.find(' ') #第一个空格
            second = content.rfind(' ')#第二个空格
            await self.tfa_cmd(message,key=content[first+1:second],vcode=content[second+1:])
        elif '/kill' in content:
            save_all_file() # 保存所有文件
            await self.msg_inform(message,f"「{self.robot.name}」准备退出")
            _log.info(f"[BOT.KILL] bot off at {GetTime()}")
            os._exit(0)
        else:
            return


# 保存所有文件的task
def save_file_task():
    while True:
        save_all_file()
        time.sleep(300)#执行一次，睡5分钟

if __name__ == "__main__":
    # 通过kwargs，设置需要监听的事件通道
    _log.info(f"[BOT.START] start at {GetTime()}")
    # 实现一个保存所有文件的task（死循环
    save_th = threading.Thread(target=save_file_task)
    save_th.start()
    _log.info(f"[BOT.START] save_all_file task start {GetTime()}")
    # 运行bot
    intents = botpy.Intents(public_guild_messages=True,direct_message=True)
    client = MyClient(intents=intents)
    client.run(appid=bot_config["appid"], token=bot_config["token"])
