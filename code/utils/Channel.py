from .file.Files import guild_config
# 配置频道，只有启用的频道才能获取信息
# 如果服务器不在文件内，则代表该服务器所有频道都可以使用
class listenConf:
    def isActivate(gid:str,chid:str):
        """- True: gid not in conf / chid in conf
           - False: gid in conf buf chid not in conf
        """
        if gid not in guild_config:
            return True
        
        if chid not in guild_config[gid]['ch']:
            return False
        
        return True

    def activateCh(gid:str):
        if gid not in guild_config:
            return None
        else:
            return guild_config[gid]['ch']