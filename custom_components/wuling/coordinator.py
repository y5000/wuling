import aiohttp
import hashlib
import json
import time
from datetime import timedelta

from homeassistant.core import HomeAssistant, State, ServiceCall, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.dt import now
from homeassistant.exceptions import IntegrationError

from .const import (
    DOMAIN, API_BASE, _LOGGER,
    sgmwnonce, sgmwappcode, sgmwappversion,
    sgmwsystem, sgmwsystemversion
)
from .converters import get_value, Converter


class StateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        # 从配置条目选项中读取保存的基本API刷新速率，默认60秒
        basic_refresh_rate = entry.options.get('basic_api_refresh_rate', 60)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{entry.entry_id}-coordinator",
            update_interval=timedelta(seconds=basic_refresh_rate),
        )
        self.entry = entry
        self.data = {}
        self.extra = {}
        self.entities = {}
        
        # 初始化刷新速率设置
        self.other_api_refresh_rate = entry.options.get('other_api_refresh_rate', 600)  # 默认10分钟
        
        # 初始化调试模式
        self.debug_mode = entry.options.get('debug_mode', False)
        
        # 初始化选中的移动设备
        self.selected_mobile_device = entry.options.get('selected_mobile_device', '')
        
        # 初始化高德API密钥（备用定位服务）
        # 当amap_key为空时，清空变量（设置为None）
        amap_key = entry.data.get('amap_key', '') or entry.options.get('amap_key', '')
        self.amap_key = amap_key if amap_key.strip() else None
        
        # 初始化最后检查时间
        self.last_check_time = 0
        self.last_tire_time = 0
        self.last_yesterday_mileage_time = 0
        
        # 初始化通知相关变量
        self.last_notification_time = time.time()  # 上次发送通知的时间戳，初始化为当前时间，避免启动时发送通知
        self.notification_active = False  # 通知是否处于激活状态
        self.previous_door_status = None  # 上一次车门状态
        self.previous_key_status = None  # 上一次钥匙状态
        
        # 初始化基本API刷新速率相关变量
        self.original_update_interval = timedelta(seconds=basic_refresh_rate)  # 保存用户原始设置的刷新速率
        self.temp_update_interval = None  # 临时调整的刷新速率
        
        # 初始化第一次启动标志
        self.first_start = True  # 系统第一次启动标志，用于跳过钥匙状态检查
        
        # 初始化转换器
        from .sensors_config import create_converters
        self.converters = create_converters()
        
        # 启动其他API的独立刷新任务
        self._async_start_other_api_refresh()

    @property
    def access_token(self):
        return self.entry.data.get(CONF_ACCESS_TOKEN, '')

    @property
    def client_id(self):
        return self.entry.data.get(CONF_CLIENT_ID, '')

    @property
    def client_secret(self):
        return self.entry.data.get(CONF_CLIENT_SECRET, '')

    @property
    def car_info(self):
        return self.data.get('carInfo') or {}

    @property
    def car_status(self):
        return self.data.get('carStatus') or {}

    @property
    def car_name(self):
        return self.car_info.get('carName', '')

    @property
    def vin(self):
        return self.car_info.get('vin', '')

    @property
    def vin_sort(self):
        vin = f'{self.vin}'.lower()
        if not vin:
            return DOMAIN
        return f'{vin[:6]}_{vin[-6:]}'

    @property
    def model(self):
        name = self.car_info.get('carTypeName', '')
        model = self.car_info.get('model', '')
        return f'{name} {model}'.strip()

    async def update_from_service(self, call: ServiceCall):
        data = call.data
        await self.async_request_refresh()
        return self.data

    async def check_auth(self):
        code = self.extra.get('errorCode')
        if code == '500009':
            msg = self.extra.get('errorMessage') or '登陆失效'
            raise IntegrationError(msg)

    def _async_start_other_api_refresh(self):
        """启动其他API的独立刷新任务"""
        import asyncio
        
        async def _refresh_other_apis():
            """定期刷新其他API的任务"""
            while True:
                try:
                    current_time = time.time()
                    refresh_interval = self.other_api_refresh_rate
                    
                    # 检查是否到达刷新时间，或者首次运行时
                    last_refresh_time = max(self.last_check_time, self.last_tire_time, self.last_yesterday_mileage_time)
                    if current_time - last_refresh_time > refresh_interval:
                      
                        # 依次刷新每个API，间隔3秒
                        
                        # 刷新检查API
                        self.last_check_time = current_time
                        await self.async_update_check()
                        await asyncio.sleep(3)
                        # 刷新轮胎API
                        self.last_tire_time = current_time
                        await self.async_update_tire()
                        await asyncio.sleep(3)
                        # 刷新昨日里程API
                        self.last_yesterday_mileage_time = current_time                            
                        await self.async_update_yesterday_mileage()
                        
                        # 通知Home Assistant更新状态
                        self.async_set_updated_data(self.data)
                    
                    # 等待1秒后再次检查
                    await asyncio.sleep(1)
                except Exception as e:
                    _LOGGER.error('Error in other APIs refresh task: %s', e)
                    # 出现错误时等待5秒后重试
                    await asyncio.sleep(5)
        
        # 取消现有的刷新任务（如果存在）
        if hasattr(self, '_other_apis_refresh_task'):
            self._other_apis_refresh_task.cancel()
        
        # 创建新的刷新任务
        self._other_apis_refresh_task = asyncio.create_task(_refresh_other_apis())

    def _wgs2gcj(self, lng, lat):
        """将WGS84坐标转换为GCJ02坐标（高德地图坐标系）"""
        earthR = 6378137
        
        def out_of_china(lat, lng):
            """检查坐标是否在中国境外"""
            return lng < 72.004 or lng > 137.8347 or lat < 0.8293 or lat > 55.8271
        
        def transform(lat, lng):
            """坐标转换核心函数"""
            ret = [0.0, 0.0]
            dLat = transform_lat(lng - 105.0, lat - 35.0)
            dLng = transform_lng(lng - 105.0, lat - 35.0)
            radLat = lat / 180.0 * 3.141592653589793
            magic = 1 - 0.006693421622965943 * (radLat * radLat)
            sqrtMagic = pow(magic, 0.5)
            ret[0] = (dLat * 180.0) / ((earthR * (1 - 0.006693421622965943) / (magic * sqrtMagic) * 3.141592653589793))
            ret[1] = (dLng * 180.0) / (earthR / sqrtMagic * cos(radLat) * 3.141592653589793)
            return ret
        
        def transform_lat(x, y):
            """计算纬度转换偏移量"""
            ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(abs(x))
            ret += (20.0 * sin(6.0 * x * 3.141592653589793) + 20.0 * sin(2.0 * x * 3.141592653589793)) * 2.0 / 3.0
            ret += (20.0 * sin(y * 3.141592653589793) + 40.0 * sin(y / 3.0 * 3.141592653589793)) * 2.0 / 3.0
            ret += (160.0 * sin(y / 12.0 * 3.141592653589793) + 320 * sin(y * 3.141592653589793 / 30.0)) * 2.0 / 3.0
            return ret
        
        def transform_lng(x, y):
            """计算经度转换偏移量"""
            ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(abs(x))
            ret += (20.0 * sin(6.0 * x * 3.141592653589793) + 20.0 * sin(2.0 * x * 3.141592653589793)) * 2.0 / 3.0
            ret += (20.0 * sin(x * 3.141592653589793) + 40.0 * sin(x / 3.0 * 3.141592653589793)) * 2.0 / 3.0
            ret += (150.0 * sin(x / 12.0 * 3.141592653589793) + 300.0 * sin(x / 30.0 * 3.141592653589793)) * 2.0 / 3.0
            return ret
        
        from math import cos, sin, sqrt, pow
        
        # 检查坐标是否在中国境外
        if out_of_china(lat, lng):
            return [lng, lat]
        
        # 计算转换偏移量
        d = transform(lat, lng)
        # 返回转换后的坐标
        return [lng + d[1], lat + d[0]]
    
    async def _get_address_from_gaode(self, longitude, latitude):
        """使用高德API将经纬度转换为地址名称"""
        if not self.amap_key:
            # 如果没有配置高德API密钥，直接返回空字符串
            return ""
        
        try:
            # 记录原始坐标
            raw_lng, raw_lat = float(longitude), float(latitude)
            
            # 将WGS84坐标转换为GCJ02坐标（高德API使用GCJ02坐标系）
            gcj_lng, gcj_lat = self._wgs2gcj(raw_lng, raw_lat)
            
            # 构建高德API请求URL
            # 逆地理编码API：https://restapi.amap.com/v3/geocode/regeo
            url = f"https://restapi.amap.com/v3/geocode/regeo?output=json&key={self.amap_key}&location={gcj_lng},{gcj_lat}"
            
            # 发送请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # 记录请求前的详细信息
                request_info = {
                    "请求URL": url,
                    "原始WGS84坐标": f"{raw_lng},{raw_lat}",
                    "转换后GCJ02坐标": f"{gcj_lng},{gcj_lat}",
                    "请求时间": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 发送请求并记录HTTP头部
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    # 记录响应状态和头部信息
                    response_headers = dict(response.headers)
                    response_status = response.status
                    
                    # 记录完整的请求和响应信息到调试日志
                    await self._write_debug_log(
                        "高德API请求详情:",
                        f"请求URL: {url}",
                        f"原始WGS84坐标: {raw_lng},{raw_lat}",
                        f"转换后GCJ02坐标: {gcj_lng},{gcj_lat}",
                        f"请求方法: GET",
                        f"响应状态码: {response_status}",
                        f"响应头部: {json.dumps(response_headers, ensure_ascii=False, indent=2)}"
                    )
                    
                    if response_status != 200:
                        error_msg = f"高德API请求失败，状态码: {response_status}"
                        _LOGGER.error(error_msg)
                        await self._write_debug_log(error_msg)
                        return ""
                    
                    # 获取响应内容
                    response_text = await response.text()
                    result = await response.json()
                    
                    # 记录完整的响应数据
                    await self._write_debug_log(
                        "高德API响应详情:",
                        f"原始响应内容: {response_text}",
                        f"解析后响应: {json.dumps(result, ensure_ascii=False, indent=2)}"
                    )
                    
                    # 检查API返回状态
                    if result.get('status') != '1':
                        error_msg = f"高德API返回错误: {result.get('info')}"
                        _LOGGER.error(error_msg)
                        await self._write_debug_log(error_msg)
                        return ""
                    
                    # 解析地址信息
                    regeocode = result.get('regeocode', {})
                    formatted_address = regeocode.get('formatted_address', '')
                    
                    # 保存完整的高德API响应到data中，用于地址传感器的属性
                    self.data['gaode_address_detail'] = {
                        'full_result': result,
                        'regeocode': regeocode,
                        'formatted_address': formatted_address,
                        'province': regeocode.get('addressComponent', {}).get('province', ''),
                        'city': regeocode.get('addressComponent', {}).get('city', ''),
                        'district': regeocode.get('addressComponent', {}).get('district', ''),
                        'township': regeocode.get('addressComponent', {}).get('township', ''),
                        'street': regeocode.get('addressComponent', {}).get('streetNumber', {}).get('street', ''),
                        'number': regeocode.get('addressComponent', {}).get('streetNumber', {}).get('number', ''),
                        'adcode': regeocode.get('addressComponent', {}).get('adcode', ''),
                        'citycode': regeocode.get('addressComponent', {}).get('citycode', ''),
                        'towncode': regeocode.get('addressComponent', {}).get('towncode', ''),
                        'distance': regeocode.get('addressComponent', {}).get('streetNumber', {}).get('distance', ''),
                        'direction': regeocode.get('addressComponent', {}).get('streetNumber', {}).get('direction', ''),
                    }
                    
                    await self._write_debug_log(f"解析得到的地址: {formatted_address}")
                    return formatted_address
        except Exception as e:
            error_msg = f"调用高德API时出错: {e}"
            _LOGGER.error(error_msg)
            await self._write_debug_log(error_msg)
            # 记录异常堆栈信息
            import traceback
            await self._write_debug_log(f"异常堆栈: {traceback.format_exc()}")
            return ""
    
    async def _async_update_data(self):
        result = await self.async_request('userCarRelation/queryDefaultCarStatus')
        data = result.pop('data', None) or {}
        self.data.update(data)
        self.extra = result
        # 保存基本API的systemTimeMillis
        if 'systemTimeMillis' in result:
            self.data['basic_api_timestamp'] = result['systemTimeMillis']
        
        # 获取地址名称（使用高德API进行逆地理编码）
        car_status = data.get('carStatus', {})
        longitude = car_status.get('longitude', '')
        latitude = car_status.get('latitude', '')
        key_status = car_status.get('keyStatus', '')
        
        # 确保经度和纬度是字符串类型，方便后续转换和比较
        longitude_str = str(longitude)
        latitude_str = str(latitude)
        
        # 系统第一次启动时，跳过钥匙状态检查，调用一次高德API
        # 之后恢复正常检查逻辑
        if self.first_start:
            # 标记第一次启动已完成
            self.first_start = False
            
            # 只检查经纬度有效性，跳过钥匙状态检查
            if longitude_str.strip() and longitude_str != "0" and latitude_str.strip() and latitude_str != "0":
                try:
                    # 调用高德API获取地址名称
                    _LOGGER.info("系统第一次启动，跳过钥匙状态检查，调用高德API")
                    address = await self._get_address_from_gaode(longitude, latitude)
                    # 将地址添加到data中，以便location实体使用
                    if address:
                        self.data['address'] = address
                except Exception as e:
                    _LOGGER.error(f"系统第一次启动调用高德API时出错: {e}")
        else:
            # 正常情况下，只当满足以下所有条件时，才执行高德API查询地址操作：
            # 1. 经度不为空且不为"0"
            # 2. 纬度不为空且不为"0"
            # 3. keyStatus不等于"0"
            if (longitude_str.strip() and longitude_str != "0" and 
                latitude_str.strip() and latitude_str != "0" and 
                key_status != "0"):
                try:
                    # 调用高德API获取地址名称
                    address = await self._get_address_from_gaode(longitude, latitude)
                    # 将地址添加到data中，以便location实体使用
                    if address:
                        self.data['address'] = address
                except Exception as e:
                    _LOGGER.error(f"获取地址时出错: {e}")
        
        # 处理车门未关通知逻辑
        await self._handle_door_notification(data)
        
        # 处理钥匙状态变化通知
        await self._handle_key_status_notification(data)
        
        # 处理动态刷新速率调整
        await self._handle_dynamic_refresh_rate(data)
        
        return self.data
    
    async def _handle_dynamic_refresh_rate(self, data):
        """处理动态刷新速率调整逻辑"""
        # 获取当前状态
        car_status = data.get('carStatus', {})
        key_status = car_status.get('keyStatus', '')
        door_lock_status = car_status.get('doorLockStatus', 0)
        
        # 确保door_lock_status是整数类型，处理字符串和整数两种情况
        try:
            door_lock_status = int(door_lock_status)
        except (ValueError, TypeError):
            door_lock_status = 0
        
        # 检查是否需要调整刷新速率
        if door_lock_status != 0 or key_status != "0":
            # 条件满足：车门未锁或钥匙未拔出，将刷新速率调整为10秒
            if self.update_interval.total_seconds() != 10:
                self.temp_update_interval = timedelta(seconds=10)
                self.update_interval = self.temp_update_interval
                _LOGGER.info(f"动态调整刷新速率为10秒，原因：钥匙状态={key_status}，车门锁状态={door_lock_status}")
        else:
            # 条件不满足：车门已锁且钥匙已拔出，恢复原始刷新速率
            if self.temp_update_interval is not None:
                self.update_interval = self.original_update_interval
                self.temp_update_interval = None
                _LOGGER.info(f"恢复原始刷新速率：{self.original_update_interval.total_seconds()}秒")
    
    async def _handle_door_notification(self, data):
        """处理车门未关通知逻辑"""
        # 检查是否选中了移动设备
        if not self.selected_mobile_device:
            return
        
        # 获取当前状态
        car_status = data.get('carStatus', {})
        key_status = car_status.get('keyStatus', '')
        door_lock_status = car_status.get('doorLockStatus', 0)
        
        # 确保door_lock_status是整数类型，处理字符串和整数两种情况
        try:
            door_lock_status = int(door_lock_status)
        except (ValueError, TypeError):
            door_lock_status = 0
        
        current_time = time.time()
        
        # 检查条件：
        # 1. 钥匙状态为0（无钥匙）
        # 2. 车门锁状态不为0（车门未锁）
        # 3. 上次发送通知已超过5分钟
        notification_condition = (
            key_status == "0" and 
            door_lock_status != 0 and
            (current_time - self.last_notification_time > 300)  # 5分钟
        )
        
        # 如果满足通知条件，发送通知
        if notification_condition:
            # 构建通知数据
            title = "警告"
            message = "车门未关"
            target = self.selected_mobile_device
            
            try:
                # 从设备ID中提取通知服务名称
                # 设备ID格式通常为 device_tracker.mobile_app_xxx，对应的通知服务为 notify.mobile_app_xxx
                notify_service = None
                
                if target.startswith("device_tracker."):
                    # 提取完整的设备名称部分
                    full_device_name = target.split(".")[1]
                    
                    # 检查是否已经是mobile_app开头
                    if full_device_name.startswith("mobile_app_"):
                        # 如果已经是mobile_app_xxx格式，直接使用
                        notify_service = full_device_name
                    else:
                        # 否则，添加mobile_app_前缀
                        notify_service = f"mobile_app_{full_device_name}"
                else:
                    # 如果不是device_tracker域，检查是否直接是mobile_app格式
                    if target.startswith("mobile_app_"):
                        notify_service = target
                    else:
                        # 否则，尝试添加mobile_app_前缀
                        notify_service = f"mobile_app_{target}"
                
                # 检查通知服务是否存在
                if self.hass.services.has_service("notify", notify_service):
                    # 调用Home Assistant的通知服务
                    await self.hass.services.async_call(
                        "notify",
                        notify_service,
                        {
                            "title": title,
                            "message": message
                        },
                        blocking=True
                    )
                    
                    # 更新通知状态
                    self.last_notification_time = current_time
                    self.notification_active = True
                    
                    # 更新数据字典中的通知时间，用于传感器显示
                    self.data['last_door_notification_time'] = current_time * 1000  # 转换为毫秒时间戳
                    
                    _LOGGER.info(f"已发送车门未关通知到设备: {target}，使用服务: notify.{notify_service}")
                else:
                    # 如果直接格式不正确，尝试使用原始设备名
                    original_service = full_device_name if 'full_device_name' in locals() else target
                    if self.hass.services.has_service("notify", original_service):
                        # 调用原始服务名
                        await self.hass.services.async_call(
                            "notify",
                            original_service,
                            {
                                "title": title,
                                "message": message
                            },
                            blocking=True
                        )
                        
                        # 更新通知状态
                        self.last_notification_time = current_time
                        self.notification_active = True
                        self.data['last_door_notification_time'] = current_time * 1000
                        
                        _LOGGER.info(f"已发送车门未关通知到设备: {target}，使用服务: notify.{original_service}")
                    else:
                        # 记录详细的调试信息
                        all_notify_services = [service for service in self.hass.services.services.get("notify", {}).keys()]
                        _LOGGER.warning(f"通知服务 notify.{notify_service} 不存在，无法发送通知到设备: {target}。可用的通知服务: {all_notify_services}")
            except Exception as e:
                _LOGGER.error(f"发送通知失败: {e}")
        
        # 当条件不再满足时，重置通知状态
        if not (key_status == "0" and door_lock_status != 0):
            self.notification_active = False
            # 不需要重置last_notification_time，因为下次满足条件时会检查时间差

    async def _handle_key_status_notification(self, data):
        """处理钥匙状态变化通知逻辑
        
        当keyStatus从非2变为2时，向移动设备发送一条通知：
        - 标题：汽车
        - 内容：汽车已启动
        
        只有在keyStatus实际变化时才发送通知，避免重复发送。
        """
        # 检查是否选中了移动设备
        if not self.selected_mobile_device:
            return
        
        # 获取当前钥匙状态
        car_status = data.get('carStatus', {})
        current_key_status = car_status.get('keyStatus', '')
        
        # 检查钥匙状态是否从非2变为2
        if (current_key_status == "2" and 
            self.previous_key_status is not None and 
            self.previous_key_status != "2"):
            
            # 构建通知数据
            title = "汽车"
            message = "汽车已启动"
            target = self.selected_mobile_device
            
            try:
                # 从设备ID中提取通知服务名称
                # 设备ID格式通常为 device_tracker.mobile_app_xxx，对应的通知服务为 notify.mobile_app_xxx
                notify_service = None
                
                if target.startswith("device_tracker."):
                    # 提取完整的设备名称部分
                    full_device_name = target.split(".")[1]
                    
                    # 检查是否已经是mobile_app开头
                    if full_device_name.startswith("mobile_app_"):
                        # 如果已经是mobile_app_xxx格式，直接使用
                        notify_service = full_device_name
                    else:
                        # 否则，添加mobile_app_前缀
                        notify_service = f"mobile_app_{full_device_name}"
                else:
                    # 如果不是device_tracker域，检查是否直接是mobile_app格式
                    if target.startswith("mobile_app_"):
                        notify_service = target
                    else:
                        # 否则，尝试添加mobile_app_前缀
                        notify_service = f"mobile_app_{target}"
                
                # 检查通知服务是否存在
                if self.hass.services.has_service("notify", notify_service):
                    # 调用Home Assistant的通知服务
                    await self.hass.services.async_call(
                        "notify",
                        notify_service,
                        {
                            "title": title,
                            "message": message
                        },
                        blocking=True
                    )
                    
                    _LOGGER.info(f"已发送汽车启动通知到设备: {target}，使用服务: notify.{notify_service}")
                else:
                    # 如果直接格式不正确，尝试使用原始设备名
                    original_service = full_device_name if 'full_device_name' in locals() else target
                    if self.hass.services.has_service("notify", original_service):
                        # 调用原始服务名
                        await self.hass.services.async_call(
                            "notify",
                            original_service,
                            {
                                "title": title,
                                "message": message
                            },
                            blocking=True
                        )
                        
                        _LOGGER.info(f"已发送汽车启动通知到设备: {target}，使用服务: notify.{original_service}")
                    else:
                        # 记录详细的调试信息
                        all_notify_services = [service for service in self.hass.services.services.get("notify", {}).keys()]
                        _LOGGER.warning(f"通知服务 notify.{notify_service} 不存在，无法发送通知到设备: {target}。可用的通知服务: {all_notify_services}")
            except Exception as e:
                _LOGGER.error(f"发送汽车启动通知失败: {e}")
        
        # 更新上一次钥匙状态
        self.previous_key_status = current_key_status

    async def async_auth_start(self):
        result = await self.async_request('car/control/ignition/authorize', data={
            'vin': self.vin,
        })
        data = result.get('data') or {}
        return data

    async def async_search_car(self):
        result = await self.async_request('car/control/searchCar', data={
            'vin': self.vin,
        })
        data = result.get('data') or {}
        return data

    async def async_control_window(self, status=0):
        result = await self.async_request('car/control/window', data={
            'vin': self.vin,
            'status': status,
        })
        data = result.get('data') or {}
        return data

    async def async_update_check(self):
        result = await self.async_request('car/check/all', json={
            'vin': self.vin,
        })
        data = result.pop('data', None) or {}
        self.data['checkStatus'] = data
        # 保存检查API的systemTimeMillis
        if 'systemTimeMillis' in result:
            self.data['check_api_timestamp'] = result['systemTimeMillis']
        return data

    async def async_update_tire(self):
        result = await self.async_request('car/info/tire/pressure', json={
            'vin': self.vin,
        })
        data = result.pop('data', None) or {}
        self.data['tirePressure'] = data
        # 保存轮胎API的systemTimeMillis
        if 'systemTimeMillis' in result:
            self.data['tire_api_timestamp'] = result['systemTimeMillis']
        return data

    async def async_update_yesterday_mileage(self):
        result = await self.async_request('car/yesterday/mileage', json={
            'vin': self.vin,
        })
        data = result.pop('data', None) or {}
        self.data['yesterdayMileage'] = data
        # 保存昨日里程API的systemTimeMillis
        if 'systemTimeMillis' in result:
            self.data['yesterday_mileage_api_timestamp'] = result['systemTimeMillis']
        return data
    
    async def async_refresh_address(self):
        """手动刷新地址信息，使用与车启动时相同的逻辑"""
        # 记录方法调用，确保按钮点击被正确响应
        _LOGGER.info("手动刷新地址按钮被点击")
        await self._write_debug_log("手动刷新地址按钮被点击")
        
        # 从当前数据中获取车辆状态
        car_status = self.data.get('carStatus', {})
        longitude = car_status.get('longitude', '')
        latitude = car_status.get('latitude', '')
        key_status = car_status.get('keyStatus', '')
        
        # 确保经度和纬度是字符串类型，方便后续转换和比较
        longitude_str = str(longitude)
        latitude_str = str(latitude)
        
        # 记录当前车辆状态，方便调试
        await self._write_debug_log(
            f"当前车辆状态：",
            f"  - 经度: {longitude_str}",
            f"  - 纬度: {latitude_str}",
            f"  - 钥匙状态: {key_status}",
            f"  - debug_mode: {self.debug_mode}"
        )
        
        # 先检查debug_mode状态，确保调试日志能正确写入
        if not self.debug_mode:
            _LOGGER.info("调试模式未开启，手动开启调试日志写入")
            # 临时开启调试日志写入，确保本次操作能被记录
            original_debug_mode = self.debug_mode
            self.debug_mode = True
        
        # 手动刷新地址时，移除钥匙状态检查，允许在任何情况下调用API
        # 保持与车启动时相同的经纬度检查逻辑
        if (longitude_str.strip() and longitude_str != "0" and 
            latitude_str.strip() and latitude_str != "0"):
            try:
                # 调用高德API获取地址名称
                _LOGGER.info("满足调用条件，开始调用高德API")
                await self._write_debug_log("满足调用条件，开始调用高德API")
                
                address = await self._get_address_from_gaode(longitude, latitude)
                # 将地址添加到data中，以便location实体使用
                if address:
                    self.data['address'] = address
                    # 发送状态更新通知
                    self.async_set_updated_data(self.data)
                    _LOGGER.info(f"手动刷新地址成功，获取到地址：{address}")
                    await self._write_debug_log(f"手动刷新地址成功，获取到地址：{address}")
                    
                    # 恢复原始debug_mode状态
                    if 'original_debug_mode' in locals():
                        self.debug_mode = original_debug_mode
                    
                    return True
                else:
                    _LOGGER.warning("手动刷新地址：未获取到有效地址")
                    self._write_debug_log("手动刷新地址：未获取到有效地址")
                    
                    # 恢复原始debug_mode状态
                    if 'original_debug_mode' in locals():
                        self.debug_mode = original_debug_mode
                    
                    return False
            except Exception as e:
                _LOGGER.error(f"手动刷新地址时出错: {e}")
                self._write_debug_log(f"手动刷新地址时出错: {e}")
                
                # 恢复原始debug_mode状态
                if 'original_debug_mode' in locals():
                    self.debug_mode = original_debug_mode
                
                return False
        else:
            # 不满足调用条件，记录日志
            _LOGGER.warning("手动刷新地址：不满足调用条件")
            _LOGGER.warning(f"  - 经度: {longitude_str}")
            _LOGGER.warning(f"  - 纬度: {latitude_str}")
            _LOGGER.warning(f"  - 钥匙状态: {key_status}")
            
            self._write_debug_log(
                "手动刷新地址：不满足调用条件",
                f"  - 经度: {longitude_str}",
                f"  - 纬度: {latitude_str}",
                f"  - 钥匙状态: {key_status}"
            )
            
            # 恢复原始debug_mode状态
            if 'original_debug_mode' in locals():
                self.debug_mode = original_debug_mode
            
            return False

    async def async_request(self, api: str, **kwargs):
        timestamp = int(time.time() * 1000)
        url = kwargs.setdefault('url', f'{API_BASE}/{api.lstrip("/")}')
        kwargs.setdefault('method', 'POST')
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=UTF-8',
            'User-Agent': 'okhttp/4.9.0',
            'channel': 'linglingbang',
            'platformNo': 'Android',
            'appVersionCode': '1677',
            'version': 'V8.2.10',
            'imei': 'a-c62b2f538bf34758',
            'imsi': 'unknown',
            'deviceModel': 'MI 8',
            'deviceBrand': 'Xiaomi',
            'deviceType': 'Android',
            'accessChannel': '1',
            'sgmwaccesstoken': self.access_token,
            'sgmwtimestamp': str(timestamp),
            'sgmwnonce': sgmwnonce,
            'sgmwclientid': self.client_id,
            'sgmwclientsecret': self.client_secret,
            'sgmwappcode': sgmwappcode,
            'sgmwappversion': sgmwappversion,
            'sgmwsystem': sgmwsystem,
            'sgmwsystemversion': sgmwsystemversion,
            'sgmwsignature': self.get_sign(timestamp, sgmwnonce),
            **kwargs.pop('headers', {}),
        }
        kwargs['headers'] = headers
        
        # 获取请求数据
        request_data = kwargs.get('json', kwargs.get('data', {}))
        
        try:
            res = await async_get_clientsession(self.hass).request(
                **kwargs,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        except Exception as err:
            _LOGGER.error('Request %s error: %s', api, err)
            # 写入调试日志
            await self._write_debug_log(
                f"API调用失败: {url}", 
                f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}",
                f"请求头部: {json.dumps(headers, ensure_ascii=False, indent=2)}",
                f"错误信息: {err}"
            )
            return {}
        text = await res.text() or ''
        try:
            result = json.loads(text) or {}
        except (TypeError, ValueError) as exc:
            _LOGGER.error('Response from %s error: %s', api, [exc, text])
            # 写入调试日志
            await self._write_debug_log(
                f"API响应解析失败: {url}", 
                f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}",
                f"请求头部: {json.dumps(headers, ensure_ascii=False, indent=2)}",
                f"响应内容: {text}", 
                f"错误信息: {exc}"
            )
            return {}
        
        # 写入调试日志
        await self._write_debug_log(
            f"API调用成功: {url}", 
            f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}",
            f"请求头部: {json.dumps(headers, ensure_ascii=False, indent=2)}",
            f"响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}"
        )
        return result
        
    async def _write_debug_log(self, *messages):
        """写入调试日志到文件"""
        import os
        from datetime import datetime
        import asyncio
        
        # 记录调试模式检查过程
        check_log = []
        check_log.append(f"调试模式检查: 当前状态={self.debug_mode}")
        
        # 只有当调试模式开启时才写入日志
        if not self.debug_mode:
            # 写入调试模式关闭的记录到Home Assistant日志，方便调试
            _LOGGER.debug('调试日志被跳过: 调试模式关闭')
            return
        
        # 调试日志文件路径
        debug_file = os.path.join(self.hass.config.config_dir, 'custom_components', 'wuling', 'debug_log.txt')
        check_log.append(f"调试日志路径: {debug_file}")
        
        # 格式化日志内容
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_lines = [f"[{timestamp}] {msg}" for msg in check_log + list(messages)]
        log_content = '\n'.join(log_lines) + '\n\n'
        
        # 定义阻塞的文件操作函数
        def _write_log_to_file():
            """在单独线程中执行的阻塞文件操作"""
            try:
                # 创建日志目录（如果不存在）
                os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                
                # 写入日志文件
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(log_content)
                return True
            except Exception as e:
                return e
        
        try:
            # 在单独的线程中执行阻塞操作
            result = await asyncio.get_running_loop().run_in_executor(None, _write_log_to_file)
            
            if result is True:
                _LOGGER.debug('调试日志写入成功')
            else:
                _LOGGER.error('写入调试日志失败: %s', result)
        except Exception as e:
            _LOGGER.error('写入调试日志失败: %s', e)

    def get_sign(self, timestamp, nonce):
        # 计算签名
        sign_str = (self.access_token +
                    str(timestamp) +
                    nonce +
                    self.client_id +
                    self.client_secret +
                    sgmwappcode +
                    sgmwappversion +
                    sgmwsystem +
                    sgmwsystemversion)
        return hashlib.md5(sign_str.encode()).hexdigest().lower()

    def decode(self, data: dict) -> dict:
        """Decode props for HASS."""
        payload = {}
        for conv in self.converters:
            prop = conv.prop or conv.attr
            value = get_value(data, prop, None)
            # 即使prop是None，也要调用decode方法，特别是对于SelectConv等特殊转换器
            conv.decode(self, payload, value)
        return payload

    def push_state(self, value: dict):
        """Push new state to Hass entities."""
        if not value:
            return
        attrs = value.keys()

        for entity in self.entities.values():
            if not hasattr(entity, 'subscribed_attrs'):
                continue
            if not (entity.subscribed_attrs & attrs):
                continue
            entity.async_set_state(value)
            if entity.added:
                entity.async_write_ha_state()

    def subscribe_attrs(self, conv: Converter):
        attrs = {conv.attr}
        if conv.childs:
            attrs |= set(conv.childs)
        attrs.update(c.attr for c in self.converters if c.parent == conv.attr)
        return attrs
