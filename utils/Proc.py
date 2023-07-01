import psutil,os
# 获取进程信息
async def get_proc_info():
    p = psutil.Process(os.getpid())
    text =f"霸占的CPU百分比：{p.cpu_percent()} %\n"
    text+=f"占用的MEM百分比：{format(p.memory_percent(), '.3f')} %\n"
    text+=f"吃下的物理内存：{format((p.memory_info().rss / 1024 / 1024), '.4f')} MB\n"
    text+=f"开辟的虚拟内存：{format((p.memory_info().vms / 1024 / 1024), '.4f')} MB\n"
    text+=f"IO信息：\n{p.io_counters()}"
    return text