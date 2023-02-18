# -*- coding: utf-8 -*-
import time

import botpy
from botpy import logging

from botpy.message import Message,DirectMessage
from botpy.types.message import MarkdownPayload, MessageMarkdownParams
from utils.valorant.ShopApi import bot_config,shop_url_post,tfa_code_post,shop_img_load
from utils.Gtime import GetTime


_log = logging.get_logger()

# help命令文字
def help_text():
    text = "以下为bot的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+= "「@机器人 /shop」查询商店\n"
    text+= "「@机器人 /uinfo」查询用户vp/rp/等级\n"
    return text

class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def handle_send_markdown_by_content(self, channel_id, msg_id):
        markdown = MarkdownPayload(content="# 标题 \n## 简介很开心 \n内容，测试")
        # 通过api发送回复消息
        await self.api.post_message(channel_id, markdown=markdown)

    # 私聊消息提醒
    async def msg_inform(self,msg:Message):
        await self.api.post_dms(
            guild_id=msg.guild_id,
            content=f"「{self.robot.name}」收到你的私信了！正在处理中……",
            msg_id=msg.id,
        )
    
    # 登录命令
    async def login_cmd(self,msg:Message):
        begin_time = time.time()
        content = msg.content
        # /login 账户 密码
        first = content.find(' ') #第一个空格
        second = content.rfind(' ')#第二个空格
        act = content[first+1:second]
        pwd = content[second+1:]
        ret = await shop_url_post(account=act,passwd=pwd)
        if ret['code']==0:
            img_bytes = await shop_img_load(img_src=ret['message'],key=act)
            # 发送图片
            await self.api.post_dms(
                guild_id=msg.guild_id,
                content=f"成功获取您的商店！",
                msg_id=msg.id,
                file_image=img_bytes
            )
            print(time.time()-begin_time)
    
    # 邮箱验证
    async def tfa_cmd(self,msg:Message):
        return
    
    # 帮助命令
    async def help_cmd(self, msg: Message):
        text = help_text()
        await msg.reply(content=text)
        _log.info(f"[help] G:{msg.guild_id} C:{msg.channel_id} Au:{msg.author.id}")

    # 获取商店
    async def shop_cmd(self,msg:Message):
        return

    # 获取uinfo
    async def uinfo_cmd(self,msg:Message):
        return

    # 监听公频消息
    async def on_at_message_create(self, message: Message):
        #await self.handle_send_markdown_by_content(message.channel_id, message.id)
        content = message.content
        if '/ahri' in content:
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
        if '/login' in message.content:
            await self.msg_inform(message)
            await self.login_cmd(message)
        elif '/tfa' in message.content:
            await self.msg_inform(message)
            await self.tfa_cmd(message)
        else:
            return


if __name__ == "__main__":
    # 通过kwargs，设置需要监听的事件通道
    print(f"[BOT.START] start at {GetTime()}")
    intents = botpy.Intents(public_guild_messages=True,direct_message=True)
    client = MyClient(intents=intents)
    client.run(appid=bot_config["appid"], token=bot_config["token"])
