<h1 align="center">QQ-Valorant-Bot</h1>

<h4 align="center">这是一个QQ频道的「Valorant」机器人</h4>

<div align="center">

![python](https://img.shields.io/badge/Python-3.8%2B-green) ![commit](https://img.shields.io/github/last-commit/musnows/QQ-Valorant-Bot) ![release](https://img.shields.io/github/v/release/musnows/QQ-Valorant-Bot)
[![khl server](https://www.kaiheila.cn/api/v3/badge/guild?guild_id=3986996654014459&style=0)](https://kook.top/gpbTwZ) ![githubstars](https://img.shields.io/github/stars/musnows/QQ-Valorant-Bot?style=social)

</div>



## 1.当前支持的命令

目前为初始版本，调用 [kook-valorant-bot](https://github.com/musnows/Kook-Valorant-Bot) 的画图Api移植而来

| Cmd        | Function                                                     |
| --------------- | ------------------------------------------------------------ |
| `/ahri` or `/help`         | 帮助命令 |
| `/login account passwd`         | 登录 riot 账户 |
| `/tfa verify-code`         | 提供邮箱验证码  |
| `/shop` or `/store`       | 查询每日商店 |
| `/uinfo`       | 查询 vp,rp,用户等级 |

QQ频道特色，所有命令在公频使用的时候，需要先at机器人

<img src="./screenshot/login.png" alt="login" height="230px">

<img src="./screenshot/shop.png" alt="shop" height="260px">

## 2.依赖项

BOT采用官方提供的 [Python sdk](https://github.com/tencent-connect/botpy)

```
pip install qq-botpy
```
sdk使用示例请查看官方git仓库中的的example

### 2.1 config

要想使用本bot，请在 `code/config` 目录下创建 `config.json` 文件

```json
{
    "appid": "机器人appid",
    "token": "机器人token",
    "val_api_url": "https://val.musnow.top/api",
    "val_api_token": "val_api_token",
    "master_id":"机器人开发者id"
}
```

其中 `val_api_token` 的获取详见 [valorant-api-docs](https://github.com/musnows/Kook-Valorant-Bot/blob/develop/docs/valorant-shop-img-api.md)

### 2.2 log

Bot运行时需要多个依赖项文件，完整的文件列表详见 [FileManage](./code/utils/FileManage.py)

请在 `code/log` 目录下创建 `UserAuthID.json`，初始化为如下字段

```json
{
  "ap_log": {},
  "data": {}
}
```

其余需要的文件均和kook机器人需要的文件同名，参考 [log.example](https://github.com/musnows/Kook-Valorant-Bot/tree/develop/docs/log.example)


### 支持本项目😘

阿狸的支出主要为云服务器的费用，您的支持是对作者的最大鼓励！

<a href="https://afdian.net/a/128ahri">
    <img src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.jpg" alt="aifadian">
</a >