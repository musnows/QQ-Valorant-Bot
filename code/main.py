# -*- coding: utf-8 -*-
import io
import os
import requests

import botpy
from botpy import logging

from botpy.message import Message,DirectMessage
from botpy.types.message import MarkdownPayload, MessageMarkdownParams
from utils.ShopApi import bot_config,shop_url_post,tfa_code_post
from utils.Gtime import GetTime
from PIL import Image


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

    async def img_test(message:Message):
        img = io.BytesIO(requests.get('https://img.kookapp.cn/assets/2022-09/lSj90Xr9yA0zk0k0.png').content)
        bg = Image.open(img)  # 16-9 商店默认背景
        imgByteArr = io.BytesIO(bg.tobytes())
        #img_bytes = bg.tobytes()
        img_bytes = img.read()
        # 只有下面这个办法可行
        # with open("./test.png", "rb") as img:
        #     img_bytes = img.read()
        print(type(img_bytes))
        print(type(img.read()))
        # await message.reply(content=f"机器人{self.robot.name}收到你的@消息了: {message.content}", file_image=img_bytes)

    async def on_at_message_create(self, message: Message):
        text = help_text()
        await message.reply(content=text)
        #await self.handle_send_markdown_by_content(message.channel_id, message.id)


    async def on_direct_message_create(self, message: DirectMessage):
        await self.api.post_dms(
            guild_id=message.guild_id,
            content=f"机器人{self.robot.name}收到你的私信了: {message.content}",
            msg_id=message.id,
        )
        if '/login' in message.content:
            content = message.content
            print(message.content)
            # /login 账户 密码
            first = content.find(' ') #第一个空格
            second = content.rfind(' ')#第二个空格
            act = content[first+1:second]
            pwd = content[second+1:]
            print(f"[{act}][{pwd}]")
            ret = await shop_url_post(account=act,passwd=pwd)
            print(ret)


if __name__ == "__main__":
    # 通过kwargs，设置需要监听的事件通道
    print(f"[BOT.START] start at {GetTime()}")
    intents = botpy.Intents(public_guild_messages=True,direct_message=True)
    client = MyClient(intents=intents)
    client.run(appid=bot_config["appid"], token=bot_config["token"])
