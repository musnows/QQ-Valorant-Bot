import time
from datetime import datetime
from zoneinfo import ZoneInfo


def GetTime():
    """获取当前时间，格式为 `23-01-01 00:00:00`"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a.strftime('%y-%m-%d %H:%M:%S')
    # use time.loacltime if you aren't using BeiJing Time
    # return time.strftime("%y-%m-%d %H:%M:%S", time.localtime())


def GetDate(format_str='%y-%m-%d'):
    """获取当前日期，默认格式为 `23-01-01`"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a.strftime(format_str)
    # use time.loacltime if you aren't using BeiJing Time
    # return time.strftime("%y-%m-%d", time.localtime())


def GetTimeStampOf8AM():
    """获取当日早上8点的时间戳（用于计算用户的商店图片是否过期）"""
    return time.mktime(
        time.strptime(f"{GetDate()} 08:00:00", "%y-%m-%d %H:%M:%S"))


def GetTimeFromStamp(timestamp: float | int):
    """通过时间戳获取当前的本地时间，格式 23-01-01 00:00:00"""
    # localtime = time.localtime(timestamp)
    # localtime_str = time.strftime("%y-%m-%d %H:%M:%S", localtime)
    a = datetime.fromtimestamp(timestamp, tz=ZoneInfo('Asia/Shanghai'))
    return a.strftime("%y-%m-%d %H:%M:%S")


def GetTimeStamp():
    """获取当前时间戳"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a.timestamp()


def GetDateTimeNow():
    """获取东八区的datetime对象"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a