import os
from .FileManage import FileManage,_log

config = FileManage("./config/config.json", True)  # 机器人配置文件
bot_config = config['bot']       
"""机器人token，botappid"""
api_config = config['val_api'] 
"""https://github.com/Valorant-Shop-CN/Kook-Valorant-Bot/blob/main/docs/valorant-shop-img-api.md"""
guild_config = config['guild']
"""机器人频道配置，参考README"""

ValSkinList = FileManage("./log/ValSkin.json")  
"""valorant皮肤"""
ValPriceList = FileManage("./log/ValPrice.json")
"""valorant皮肤价格"""
ValBundleList = FileManage("./log/ValBundle.json")
"""valorant捆绑包"""
ValItersList = FileManage("./log/ValIters.json")
"""valorant皮肤等级"""
SkinRateDict = FileManage("./log/ValSkinRate.json")
"""valorant皮肤评分信息"""

UserAuthID = FileManage("./log/UserAuthID.json")
"""用户游戏id/uuid，账户密码重登记录"""
UserPwdReauth = UserAuthID['ap_log']
"""账户密码重登记录"""
UserAuthCache = {'acpw':{},'data':{},'qqbot':{},'tfa':{}} 
"""存放用户的登录class，不需要保存到本地
- {'acpw':{},'data':{},'qqbot':{},'tfa':{}} 
"""
UserShopBgDict = FileManage("./log/UserShopBg.json")
"""背景图设置；商店图缓存"""
UserRtsDict = {}
"""用户皮肤评分选择列表"""

_log.info(f"[File] load all files") # 走到这里代表所有文件都打开了

LogPath = ['./log','./log/cookie/','./log/img_temp/weapon','./log/img_temp/comp','./log/img_temp/169/comp/','./log/mission/']
"""自动创建存放商店图片缓存的文件夹"""
for path in LogPath:
    if(not os.path.exists(path)):
        os.makedirs(path) # 文件夹不存在，创建
        _log.debug(f"[File] create path {path}")

_log.info(f"[File] create all path") # 走到这里代表所有文件夹都创建了