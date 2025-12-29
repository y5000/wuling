from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional, TYPE_CHECKING
from homeassistant.const import EntityCategory
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
import logging

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .. import StateCoordinator as Client


def get_value(obj, key, def_value=None):
    keys = f'{key}'.split('.')
    result = obj
    for k in keys:
        if result is None:
            return def_value
        if isinstance(result, dict):
            result = result.get(k, def_value)
        elif isinstance(result, (list, tuple)):
            try:
                result = result[int(k)]
            except (ValueError, IndexError):
                result = def_value
    return result


@dataclass
class Converter:
    attr: str  # hass attribute
    domain: Optional[str] = None  # hass domain

    prop: Optional[str] = None
    parent: Optional[str] = None

    enabled: Optional[bool] = True  # support: True, False, None (lazy setup)
    poll: bool = False  # hass should_poll

    # don't init with dataclass because no type:
    childs: Optional[set] = None
    option = None

    # to hass
    def decode(self, client: "Client", payload: dict, value: Any):
        payload[self.attr] = value

    # from hass
    def encode(self, client: "Client", payload: dict, value: Any):
        payload[self.prop or self.attr] = value

    def with_option(self, option: dict):
        self.option = option
        return self

@dataclass
class BoolConv(Converter):
    reverse: bool = None

    def decode(self, client: "Client", payload: dict, value: Any):
        # 处理调试模式开关
        if self.attr == 'debug_mode':
            # 从协调器获取当前调试模式值
            payload[self.attr] = client.debug_mode
            return
        
        # 处理其他布尔值
        val = True if value else False
        if value in ['0', 'no', 'off', 'false']:
            val = False
        val = (not val) if self.reverse else bool(val)
        payload[self.attr] = val

    def encode(self, client: "Client", payload: dict, value: bool):
        val = (not value) if self.reverse else value
        
        # 处理调试模式开关
        if self.attr == 'debug_mode':
            # 保存到协调器对象
            client.debug_mode = val
            # 保存到配置条目选项
            options = {**client.entry.options, 'debug_mode': val}
            client.hass.config_entries.async_update_entry(
                client.entry, options=options
            )
            # 不返回任何值，保持与父类方法一致
            return
        
        super().encode(client, payload, int(val))

@dataclass
class MapConv(Converter):
    map: dict = None
    default: Any = None

    def decode(self, device: "Client", payload: dict, value: int):
        payload[self.attr] = self.map.get(value, self.default)

    def encode(self, device: "Client", payload: dict, value: Any):
        value = next(k for k, v in self.map.items() if v == value)
        super().encode(device, payload, value)

@dataclass
class SensorConv(Converter):
    domain: Optional[str] = 'sensor'

@dataclass
class BinarySensorConv(BoolConv):
    domain: Optional[str] = 'binary_sensor'

@dataclass
class NumberSensorConv(SensorConv):
    ratio: Optional[float] = 1
    precision: Optional[int] = 1
    ignore_zero: Optional[bool] = False

    def decode(self, client: "Client", payload: dict, value: Any):
        # 如果value是None，可能是因为prop为None（动态分配值的实体）
        # 这种情况下，我们不做任何处理，因为值会由其他转换器（如TireTempConv）动态分配
        if value is not None:
            try:
                val = float(f'{value}'.strip())
                val = val * self.ratio
                val = round(val, self.precision)
            except (TypeError, ValueError):
                val = None
            
            # 如果设置了ignore_zero且值为0，则不更新当前值
            if self.ignore_zero and val == 0:
                # 检查协调器的data字典中是否已有该属性的当前值
                # 这样可以确保在多次刷新之间保持非零值
                if self.attr in client.data:
                    # 如果已有值且不为0，则使用当前值，不覆盖
                    current_value = client.data.get(self.attr)
                    if current_value != 0:
                        # 使用当前值，不更新为0
                        payload[self.attr] = current_value
                    else:
                        # 如果当前值也是0，则仍需设置，避免实体消失
                        payload[self.attr] = val
                else:
                    # 如果没有当前值（首次设置），则设置值
                    payload[self.attr] = val
            else:
                # 正常更新值
                payload[self.attr] = val

@dataclass
class TireTempConv(Converter):
    """轮胎温度转换器，根据local_tire_temp分配tire_temp值到对应的轮胎温度实体"""
    domain: Optional[str] = 'sensor'
    
    def decode(self, client: "Client", payload: dict, value: Any):
        """解码轮胎温度，根据local_tire_temp分配到对应轮胎"""
        # 获取当前的轮胎温度和轮胎位置
        try:
            tire_temp = float(f'{client.data.get("tirePressure", {}).get("tirTemp", "0")}'.strip())
            tire_pos = int(f'{client.data.get("tirePressure", {}).get("locTirTemp", "-1")}'.strip())
        except (TypeError, ValueError):
            tire_temp = 0
            tire_pos = -1
        
        # 根据轮胎位置分配温度值
        if tire_pos == 0:
            # 左前轮
            payload['tire_temp_lf'] = round(tire_temp, 1)
        elif tire_pos == 1:
            # 右前轮
            payload['tire_temp_rf'] = round(tire_temp, 1)
        elif tire_pos == 2:
            # 左后轮
            payload['tire_temp_lr'] = round(tire_temp, 1)
        elif tire_pos == 3:
            # 右后轮
            payload['tire_temp_rr'] = round(tire_temp, 1)

@dataclass
class MapSensorConv(MapConv, SensorConv):
    domain: Optional[str] = 'sensor'

@dataclass
class ButtonConv(Converter):
    domain: Optional[str] = 'button'
    press: Optional[str] = ''

    def encode(self, client: "Client", payload: dict, value: Any):
        async def press(*args, **kwargs):
            if self.press and hasattr(client, self.press):
                return await getattr(client, self.press)()
            return False
        return press

@dataclass
class BaseInfoConv(Converter):
    """基本信息合并转换器"""
    domain: Optional[str] = 'sensor'
    
    def decode(self, client: "Client", payload: dict, value: Any):
        """将指定的基本信息合并到一个实体中"""
        # 直接从client.data中获取所有基本信息
        car_info = client.data.get('carInfo', {})
        
        # 设置主状态为车辆名称
        payload[self.attr] = car_info.get('carName', "未知车辆")
        
        # 只返回用户要求的属性
        required_attrs = {
            'car_name': 'carName',           # 车辆昵称
            'car_type_name': 'carTypeName',  # 车型名称
            'car_year': 'carYear',           # 车型年款
            'model': 'model',               # model
            'color_name': 'colorName',       # 颜色名称
            'vin': 'vin',                   # 车辆识别码
            'car_image': 'image',            # 车辆图片
            'car_info_id': 'carInfoId',      # 车辆信息ID
            'vsn': 'vsn',                   # 车辆序列号
            'series_code': 'seriesCode',     # 车系代码
            'purchase_shop_num': 'purchaseShopNum',  # 购买店铺编号
            'purchase_user_name': 'purchaseUserName',  # 购买人姓名
            'color_code': 'colorCode',       # 颜色代码
            'user_id': 'userId',             # 用户ID
        }
        
        # 只添加指定的属性到payload
        for attr_name, car_info_key in required_attrs.items():
            if car_info_key in car_info:
                payload[attr_name] = car_info[car_info_key]

@dataclass
class TimeStampConv(SensorConv):
    """时间戳转换器，将毫秒级时间戳转换为datetime对象"""
    domain: Optional[str] = 'sensor'
    
    def decode(self, client: "Client", payload: dict, value: Any):
        """将毫秒级时间戳转换为datetime对象"""
        try:
            if value is None:
                payload[self.attr] = None
                return
            
            # 将毫秒级时间戳转换为秒级时间戳
            if isinstance(value, (int, float)):
                value = value / 1000
            
            # 转换为datetime对象
            from datetime import datetime
            from homeassistant.util.dt import as_local
            dt = datetime.fromtimestamp(value)
            # 转换为本地时间
            local_dt = as_local(dt)
            payload[self.attr] = local_dt
        except (TypeError, ValueError) as e:
            _LOGGER.error('Failed to convert timestamp %s: %s', value, e)
            payload[self.attr] = None

@dataclass
class NumberConv(Converter):
    """Number entity converter"""
    domain: Optional[str] = 'number'
    
    def decode(self, client: "Client", payload: dict, value: Any):
        """Decode value for HASS."""
        # 对于设置实体，我们需要从协调器获取当前值
        if self.attr == 'basic_api_refresh_rate':
            payload[self.attr] = client.update_interval.total_seconds()
        elif self.attr == 'other_api_refresh_rate':
            # 检查协调器是否保存了用户设置的值
            if hasattr(client, 'other_api_refresh_rate'):
                payload[self.attr] = client.other_api_refresh_rate
            else:
                # 首次初始化时使用默认值300秒
                payload[self.attr] = 300  # 默认5分钟
        else:
            payload[self.attr] = value
    
    def encode(self, client: "Client", payload: dict, value: Any):
        """Encode value from HASS."""
        # 创建并返回一个协程对象
        async def _encode():
            if self.attr == 'basic_api_refresh_rate':
                # 更新基本API的刷新速率
                new_interval = timedelta(seconds=value)
                
                # 更新原始刷新速率，用于动态调整后恢复
                client.original_update_interval = new_interval
                
                # 如果当前不是临时调整状态，直接更新刷新速率
                if client.temp_update_interval is None:
                    client.update_interval = new_interval
                
                # 保存到配置条目选项
                options = {**client.entry.options, 'basic_api_refresh_rate': value}
                client.hass.config_entries.async_update_entry(
                    client.entry, options=options
                )
                return {self.attr: value}
            elif self.attr == 'other_api_refresh_rate':
                # 更新其他API的刷新速率
                # 保存用户设置的值到协调器对象
                client.other_api_refresh_rate = value
                # 保存到配置条目选项
                options = {**client.entry.options, 'other_api_refresh_rate': value}
                client.hass.config_entries.async_update_entry(
                    client.entry, options=options
                )
                # 修改协调器中的相关变量，使其立即重新获取数据
                client.last_check_time = 0
                client.last_tire_time = 0
                client.last_yesterday_mileage_time = 0
                # 重启其他API的独立刷新任务
                client._async_start_other_api_refresh()
                return {self.attr: value}
            return {}
        return _encode()

@dataclass
class SelectConv(Converter):
    """Select entity converter"""
    domain: Optional[str] = 'select'
    
    def decode(self, client: "Client", payload: dict, value: Any):
        """Decode value for HASS."""
        # 获取所有状态，然后过滤出device_tracker域的实体
        all_states = client.hass.states.async_all()
        device_tracker_entities = [state for state in all_states if state.domain == "device_tracker"]
        mobile_devices = []
        
        # 收集所有移动设备，改进过滤逻辑
        for entity in device_tracker_entities:
            entity_id = entity.entity_id
            name = entity.name or entity_id.split('.')[-1]
            attributes = dict(entity.attributes)
            
            # 改进的移动设备检测逻辑：确保显示真正的移动设备
            is_mobile = False
            entity_id_lower = entity_id.lower()
            
            # 检测移动设备的优先级顺序：
            # 1. 首先检查platform是否为mobile_app（最可靠的判断）
            if "platform" in attributes and attributes["platform"] == "mobile_app":
                is_mobile = True
            # 2. 检查entity_id是否明确标识为移动应用设备
            elif entity_id_lower.startswith("device_tracker.mobile_app_"):
                is_mobile = True
            # 3. 检查source_type是否为gps（GPS设备通常是移动设备）
            elif "source_type" in attributes and attributes["source_type"] == "gps":
                is_mobile = True
            # 4. 检查entity_id是否包含移动设备相关关键词
            elif any(keyword in entity_id_lower for keyword in ["mobile", "phone", "iphone", "android"]):
                is_mobile = True
            
            # 排除未知设备
            if is_mobile and "unknown" not in entity_id_lower:
                mobile_devices.append({"value": entity_id, "label": name})
        
        # 添加"清空"选项，让用户可以选择什么都不选
        mobile_devices.insert(0, {"value": "", "label": "清空"})
        
        # 将移动设备转换为选项列表
        options = [device["value"] for device in mobile_devices]
        # 保存设备标签映射，用于显示名称
        if not hasattr(client, 'mobile_device_labels'):
            client.mobile_device_labels = {}
        client.mobile_device_labels.update({device["value"]: device["label"] for device in mobile_devices})
        
        # 设置选项
        payload["options"] = options
        
        # 设置当前选中值（如果有保存的话）
        selected_value = ""
        if hasattr(client, 'selected_mobile_device'):
            selected_value = client.selected_mobile_device
        
        # 确保选中的值在选项列表中，如果不在则尝试通过设备名称匹配
        if selected_value not in options and selected_value != "":
            # 尝试通过设备名称找到匹配的设备
            saved_device_name = client.mobile_device_labels.get(selected_value, "")
            if saved_device_name:
                for device in mobile_devices:
                    if device["label"] == saved_device_name and device["value"] != "":
                        selected_value = device["value"]
                        break
                else:
                    # 没有找到匹配的设备，使用默认值
                    selected_value = ""
        
        payload[self.attr] = selected_value
    
    def encode(self, client: "Client", payload: dict, value: Any):
        """Encode value from HASS."""
        # 保存选中的移动设备
        client.selected_mobile_device = value
        # 保存到配置条目选项
        options = {**client.entry.options, 'selected_mobile_device': value}
        client.hass.config_entries.async_update_entry(
            client.entry, options=options
        )
        return {self.attr: value}
