import copy
import requests
from apscheduler.schedulers.background import BackgroundScheduler

from .file.FileManage import save_all_file
from .file.Files import SkinRateDict,_log,config
from .shop.ShopApi import shop_cmp_post

# 更新商店排行榜任务
def shop_cmp_post_task():
    # 清空已有数据
    SkinRateDict["kkn"] = copy.deepcopy(SkinRateDict["cmp"])
    SkinRateDict["cmp"]["best"]["list_shop"] = list()
    SkinRateDict["cmp"]["best"]["rating"] = 0
    SkinRateDict["cmp"]["best"]["user_id"] = "0"
    SkinRateDict["cmp"]["worse"]["list_shop"] = list()
    SkinRateDict["cmp"]["worse"]["rating"] = 100
    SkinRateDict["cmp"]["worse"]["user_id"] = "0"

    # 更新到db
    ret = shop_cmp_post(SkinRateDict["kkn"]["best"],SkinRateDict["kkn"]["worse"])
    _log.info(f"[ShopCmp.TASK] {ret.json()}")

def bot_alive_ping_task():
    """ping uptime"""
    ret = requests.get(config["ping_task_url"])
    _log.info(f"[BOT.ALIVE.TASK] requests status = {ret.status_code}")

# 运行两个任务
def start(time:str):
    """运行文件保存任务和早八商店更新任务
    """
    # 创建调度器BackgroundScheduler，不会阻塞线程
    sched = BackgroundScheduler(timezone='Asia/Shanghai')
    # 1.保存所有文件的task (每五分钟执行一次)
    sched.add_job(save_all_file, 'interval', minutes=5, id='save_all_file_task')
    # 2.早八商店评价更新（每天早八执行）
    sched.add_job(shop_cmp_post_task, 'cron',hour='8',minute='1',id='update_ShopCmt_task')
    # 3.请求uptime告知自己的在线状态
    if "ping_task_url" in config and "http" in config["ping_task_url"]:
        _log.info(f"[BOT.INIT.TASK] add_job bot_alive_ping_task")
        bot_alive_ping_task() # 立刻执行一次
        sched.add_job(bot_alive_ping_task,'interval',minutes=2, id='bot_alive')
    # 开跑
    sched.start()
    _log.info(f"[BOT.INIT.TASK] all task start {time}")