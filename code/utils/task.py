import time
import copy
import threading
from apscheduler.schedulers.background import BackgroundScheduler

from .file.FileManage import save_all_file
from .file.Files import SkinRateDict,_log
from .shop import ShopApi

# 更新商店排行榜任务
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

# 运行两个任务
def start(time:str):
    """运行文件保存任务和早八商店更新任务
    """
    # 创建调度器BackgroundScheduler，不会阻塞线程
    sched = BackgroundScheduler(timezone='Asia/Shanghai')
    # 1.保存所有文件的task (每五分钟执行一次)
    sched.add_job(save_all_file, 'interval', minute='5', id='save_all_file_task')
    # 2.早八商店评价更新（每天早八执行）
    sched.add_job(shop_cmp_post_task, 'cron',hour='8',minute='1',id='update_ShopCmt_task')
    # 开跑
    sched.start()
    _log.info(f"[BOT.START] update_ShopCmt/save_all_file task start {time}")