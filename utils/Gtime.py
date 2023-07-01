import time


#将获取当前时间封装成函数方便使用
def GetTime():
    return time.strftime("%y-%m-%d %H:%M:%S", time.localtime())


#将获取当前日期成函数方便使用
def GetDate():
    return time.strftime("%y-%m-%d", time.localtime())


# 获取当日早上8点的时间戳（用于计算用户的商店图片是否过期）
def GetTimeStampOf8AM():
    return time.mktime(time.strptime(f"{GetDate()} 08:00:00", "%y-%m-%d %H:%M:%S"))


def GetTimeFromStamp(timestamp:float|int):
    """通过时间戳获取当前的本地时间，格式 23-01-01 00:00:00"""
    localtime = time.localtime(timestamp)
    localtime_str = time.strftime("%y-%m-%d %H:%M:%S", localtime)
    return localtime_str