import os
import cnlunar as cl
import datetime as dt
import json as js
from astral import LocationInfo, sun
import time as tm
import requests as rq
import pytz
import re

SEASON_DIC = {"春":"spring", "夏":"summer", "秋":"autumn", "冬":"winter"}
OPPO_SEASON_DIC = {"autumn":"spring", "winter":"summer", "spring":"autumn", "summer":"winter"}
TIME_DIC = ["night", "dawn", "noon", "dusk", "night"]

IPINFO_URL = "http://ip-api.com/json/"
# IPINFO_URL = "http://freeapi.ipip.net/"

def init(): # 初始化路径数据
    global PATH, IMG_PATH, IMG_LST
    PATH = os.getcwd()
    static_PATH = os.path.join(PATH, "static")
    IMG_PATH = os.path.join(static_PATH, "view")
    IMG_LST = os.listdir(IMG_PATH)

def get_ChinaSeason() -> str: # 获取中国的季节
    time = dt.datetime.utcnow() + dt.timedelta(hours=8)# not dt.datetime.now(), beacuse we need UTC+8(China) to calculate cnlunar season
    today_lunar = cl.Lunar(time, godType=f'8char') #创建农历日期对象
    today_season = today_lunar.lunarSeason #获取季节
    return SEASON_DIC[today_season[-1]] #转为所需格式


def is_private_ip(ip):
    private_ip_patterns = [
        r'^10\.',                # 10.0.0.0 - 10.255.255.255
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0 - 172.31.255.255
        r'^192\.168\.',          # 192.168.0.0 - 192.168.255.255
        r'^127\.'                # 127.0.0.0 - 127.255.255.255 (loopback)
    ]
    for pattern in private_ip_patterns:
        if re.match(pattern, ip):
            return True
    return False

class IP_VIEW:
    def __init__(self):
        self.ipInfo = None # dict:"timezone"：str->dt.timezone, "latitude":float, "longitude":float 存档获取结果
        self.season = None # str 存档计算结果：季节
        self.periods = None # list 存档计算结果：时间区间列表
        self.date = None # dt.datetime 存档计算结果的调用时间

    def _get_ipInfo(self, ip: str)->None: # 获取ip信息
        rq_url = f"{IPINFO_URL}{ip}"
        try:
            res = rq.get(rq_url).text
        except rq.RequestException:
            print("[ERROR] Failed to request :(")
            return
        if res:
            res = js.loads(res)
            if res['status'] == 'success':
                self.ipInfo =\
                    {"timezone": res["timezone"],\
                     "latitude": res["lat"],\
                     "longitude": res["lon"],\
                     }
                return

        print("[ERROR] Succeeded in request. However, the response is not valid :(")
        print(res);print()
        
    def _get_timezone(self)->None: # 改写时区（str->dt.timezone）
        timezone_str = self.ipInfo["timezone"]
        try:
            timezone = pytz.timezone(timezone_str)  
        except pytz.UnknownTimeZoneError:
            return None  # 如果时区无效，返回None
        utc_offset = timezone.utcoffset(dt.datetime.now())
        self.ipInfo["timezone"] = dt.timezone(utc_offset)
    
    def _get_season(self, China_season:str)->None: #计算季节
        if self.ipInfo["latitude"] < 0:
            self.season = OPPO_SEASON_DIC[China_season]
        else:
            self.season = China_season

    def _get_periods(self)->None: # 计算当天时间区间列表
        time = self.date
        current_timezone = self.ipInfo["timezone"]
        ipInfo = self.ipInfo
        location = LocationInfo('User', 'China', ipInfo["timezone"], ipInfo["latitude"], ipInfo["longitude"]) #创建地点对象
        s = sun.sun(location.observer, date = time, tzinfo = ipInfo["timezone"]) #计算太阳时段

        tz_off = lambda x:x.replace(tzinfo = self.ipInfo["timezone"])
        self.periods = list(map(tz_off, [s["dawn"], s["sunrise"], s["sunset"], s["dusk"]]))

    def _loc_period(self)->int: # 定位时间段
        time = self.date
        periods = self.periods
        loc = 0

        while  loc < len(periods) and time > periods[loc]: #定位
            loc += 1
        return loc

    def _get_img(self, period_now:int)->str: # 确定图片
        season = self.season
        period_now_ = TIME_DIC[period_now]
        file = None
        for i in IMG_LST: #寻找所需壁纸文件
            if season in i:
                if period_now_ in i:
                    file = i
                    break
        if file is None: # 未知原因导致了未匹配
            print( "[warning: failed to get resource image due to a unknow problem. Use default image instead.]")
            file = "Main_noon_bg_summer.png"
        return file
    
    def _get_light(self, period_now:int)->False: # 判断光亮与否
        season = self.season
        period_now_ = TIME_DIC[period_now]
        return period_now_ in ["noon"]

    def _is_same_day(self)->bool: # 判断记录的时间是不是和当前同一天
        date1 = self._convert_timezone()
        date2 = self.date
        year1, month1, day1 = date1.year, date1.month, date1.day  
        year2, month2, day2 = date2.year, date2.month, date2.day  
        if year1 == year2 and month1 == month2 and day1 == day2:  
            return True
        else:  
            return False

    def _convert_timezone(self)->dt.datetime: # 获取ip所在地时间
        # 获取当前时区、时间
        time = dt.datetime.utcnow()
        current_timezone = pytz.timezone('UTC')
        # 将时间转换为UTC  
        utc_time = time.replace(tzinfo=current_timezone)  
        # 将UTC时间转换为目标时区  
        target_timezone = self.ipInfo["timezone"]
        target_time = utc_time.astimezone(target_timezone)
        return target_time

    def refresh(self, ip:str, China_season:str)->str:
        if None in (self.ipInfo, self.date, self.periods, self.season): # 存在缺失信息
            try:
                self._get_ipInfo(ip)
                self._get_timezone()
                self.date = self._convert_timezone()
            # 获取基础信息
            except:
                return None # 获取过程中报错
        if None in (self.ipInfo, self.date): # 存在基础信息缺失
            return None
        if self._is_same_day(): # 不同一天，需要重新计算数据
            self._get_periods()
            self._get_season(China_season)
        
        period_now = self._loc_period()
        return (self._get_img(period_now), self._get_light(period_now))
    
