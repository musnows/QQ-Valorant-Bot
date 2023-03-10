from .FileManage import FileManage,_log

config = FileManage("./config/config.json", True)  # 机器人配置文件
bot_config = config['bot']        # 机器人token，botappid
guild_config = config['guild']    # 机器人频道配置

ValSkinList = FileManage("./log/ValSkin.json")  # valorant皮肤
ValPriceList = FileManage("./log/ValPrice.json")  # valorant皮肤价格
ValBundleList = FileManage("./log/ValBundle.json")  # valorant捆绑包
ValItersList = FileManage("./log/ValIters.json")  # valorant皮肤等级
SkinRateDict = FileManage("./log/ValSkinRate.json")  # valorant皮肤评分信息

UserAuthID = FileManage("./log/UserAuthID.json")  # 用户游戏id/uuid，账户密码重登记录
UserTokenDict = UserAuthID['data']  # riot用户游戏id和uuid
UserPwdReauth = UserAuthID['ap_log']    # 账户密码重登记录
UserAuthDict = {'acpw':{},'data':{}} # 存放用户的登录class，不需要保存到本地
UserRtsDict = {} # 用户皮肤评分选择列表

_log.info(f"[FileManage] load all files") # 走到这里代表所有文件都打开了