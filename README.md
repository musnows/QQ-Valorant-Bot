# QQ-Valorant-Bot

qq频道valorant机器人


目前为初始版本，调用 kook-valorant-bot 的api移植而来
```python
def help_text():
    text = "以下为bot的命令列表\n"
    text+= "「/login 账户 密码」登录拳头账户，必须私聊使用\n"
    text+= "「/tfa 验证码」提供邮箱验证码，必须私聊使用\n"
    text+= "「@机器人 /shop」查询商店\n"
    text+= "「@机器人 /uinfo」查询用户vp/rp/等级\n"
    return text
```