# 如果需要本地画图，不依赖于kook bot的api，则将main中的ShopApi替换为本文件
# 本文件中的函数和ShopApi中的shop_draw_get参数一致，切换后即可使用
# 阿狸bot依旧依赖于kook bot，因为云服务器内存不足以缓存两个平台的画图资源（笑哭）
import time
import io
from PIL import PngImagePlugin,Image
from . import ShopRate,ShopImgDraw
from ..file.Files import _log
from .ShopApi import img_requestor

img_bak_169 = 'https://img.kookapp.cn/assets/2022-10/KcN5YoR5hC0zk0k0.jpg'
"""默认的16-9背景图"""
img_bak_11 = 'https://img.kookapp.cn/assets/2023-01/lzRKEApuEP0rs0rs.jpg'
"""默认的1-1背景图"""

# 存本地再打开(很蠢但是没办法)
async def shop_img_bytes(img:PngImagePlugin.PngImageFile)->bytes:
    """通过io获取pil图片字节流"""
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    img_bytes = imgByteArr.getvalue()
    return img_bytes


async def shop_img_test(message):
    """"测试用"""
    try:
        img = io.BytesIO(await img_requestor(img_bak_169))
        bg = Image.open(img)
        imgByteArr = io.BytesIO()
        bg.save(imgByteArr, format='PNG')
        img_bytes = imgByteArr.getvalue()
        print(type(imgByteArr),type(bg),type(img_bytes),type(img.read()))
        for i in range(5):
            try:
                await message.reply(content="这是一个测试",file_image=img_bytes)
                _log.info("success")
                break
            except Exception as result:
                _log.error(f"err {i} | {result}")
    except:
        _log.exception("err")


# 基本画图操作
async def base_img_draw(list_shop, vp1=0, rp1=0,img_src:str="",img_ratio:str="0") -> dict:
    """return
    - { 'code':0,'type':'url','message': img_url}
    - { 'code':0,'type':'pil','message': bg }
    - { 'code':200,'type':'error','message':err_str}
    """
    # 开始画图
    ret = { "status": False,"value":"no need to img draw"} # 初始化ret为不需要画图
    cacheRet = {"status":False,"img_url":"err" } # 是否需要上传图片(false代表需要)
    start = time.perf_counter()
    if img_ratio == '1':
        # 是1-1的图片，检测有没有使用自定义背景图
        if img_src == img_bak_11: # 没有自定义背景图
            # 检测是否有缓存命中
            cacheRet = await ShopRate.query_ShopCache(list_shop)
        # 缓存命中失败(需要画图)
        if not cacheRet['status']:
            ret = await ShopImgDraw.get_shop_img_11(list_shop, bg_img_src=img_src)
    else:  # 只有16-9的图片需获取vp和r点
        ret = await ShopImgDraw.get_shop_img_169(list_shop, vp=vp1, rp=rp1, bg_img_src=img_src)
    # 打印计时
    _log.info(f"Api imgDraw | {format(time.perf_counter() - start, '.3f')}")  # 结果为浮点数，保留两位小数

    # 判断缓存是否命中
    if cacheRet['status']: # 命中了
        dailyshop_img_src = cacheRet['img_url']
        _log.info(f"Api imgUrl(cache) | {dailyshop_img_src}")
        return { 'code':0,'type':'url','message': dailyshop_img_src }
    # 缓存没有命中，但是获取画图结果成功
    if ret['status']:
        bg = ret['value'] # 这个值是pil的结果
        return { 'code':0,'type':'pil','message': bg }
    else: # 出现图片违规或者背景图url无法获取
        err_str = ret['value']
        _log.error(err_str)
        return {'code':200,'type':'error','message':err_str}

# 画图接口(仅画图)
async def img_draw(list_shop:list,vp='0',rp='0',img_src='',img_ratio='0'):
    """return
    - { 'code':0,'type':'url','message': img_url }
    - { 'code':0,'type':'pil','message': bg }
    - { 'code':200,'type':'error','message':err_str}
    """
    # 判断传入的皮肤数量是不是4个
    if len(list_shop)!=4:raise Exception(f"list_shop len err! {len(list_shop)}")
    _log.debug(f"list_shop: {list_shop} | vp/rp: {vp}/{rp} | img_src:{img_src} | img_ratio: {img_ratio}")

    # 自定义背景
    if 'http' not in img_src:
        img_src = img_bak_169 if img_ratio != '1' else img_bak_11
    
    return await base_img_draw(list_shop, int(vp), int(rp),img_src,img_ratio)
