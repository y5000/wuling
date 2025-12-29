from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, _LOGGER, DOOR_WINDOW_ENTITIES, LIGHT_ENTITIES, BASIC_INFO_ENTITIES, TIRE_ENTITIES, SETTINGS_ENTITIES
from .converters import Converter
from .coordinator import StateCoordinator


class XEntity(CoordinatorEntity):
    log = _LOGGER
    added = False
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator: StateCoordinator, conv: Converter, option=None):
        super().__init__(coordinator)
        self.conv = conv
        self.attr = conv.attr
        self.hass = coordinator.hass
        self.entry = coordinator.entry
        self._option = option or {}
        if hasattr(conv, 'option'):
            self._option.update(conv.option or {})
        self.entity_id = f'{conv.domain}.{coordinator.vin_sort}_{conv.attr}'
        self._attr_unique_id = f'{DOMAIN}-{self.entry.entry_id}-{self.attr}'
        self._attr_icon = self._option.get('icon')
        self._attr_device_class = self._option.get('device_class')
        self._attr_entity_picture = self._option.get('entity_picture')
        self._attr_entity_category = self._option.get('entity_category')
        self._attr_translation_key = self._option.get('translation_key', conv.attr)
        
        # 确保设备名称不为空
        base_name = coordinator.car_name or "五菱汽车"
        
        # 确保标识符不为空
        base_identifier = coordinator.vin or DOMAIN
        
        # 设备类型映射
        device_type = None
        if self.attr in DOOR_WINDOW_ENTITIES:
            device_type = "door_window"
            device_name = "门窗系统"
        elif self.attr in LIGHT_ENTITIES:
            device_type = "light"
            device_name = "灯光系统"
        elif self.attr in BASIC_INFO_ENTITIES:
            device_type = "basic_info"
            device_name = "基本信息"
        elif self.attr in TIRE_ENTITIES:
            device_type = "tire"
            device_name = "轮胎系统"
        elif self.attr in SETTINGS_ENTITIES:
            device_type = "settings"
            device_name = "设置"
        
        # 创建设备信息
        if device_type:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{base_identifier}_{device_type}")},
                name=f"{base_name}-{device_name}",
                model=coordinator.model,
            )
        else:
            # 其他实体使用默认设备
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, base_identifier)},
                name=base_name,
                model=coordinator.model,
            )
        
        # 优先使用option中的设置，如果没有则使用conv.enabled的值
        self._attr_entity_registry_enabled_default = self._option.get('entity_registry_enabled_default', conv.enabled is not False)
        self._attr_extra_state_attributes = {}
        self._vars = {}
        self.subscribed_attrs = coordinator.subscribe_attrs(conv)
        coordinator.entities[conv.attr] = self

    @property
    def vin(self):
        return self.coordinator.vin

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if hasattr(self, 'async_get_last_state'):
            state = await self.async_get_last_state()
            if state and state.state:
                self.async_set_state({self.attr: state.state})
        self.added = True
        self.update()

    def update(self):
        """Update entity state from coordinator data."""
        payload = self.coordinator.decode(self.coordinator.data)
        self.coordinator.push_state(payload)

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if hasattr(self.coordinator, 'entities') and self.attr in self.coordinator.entities:
            del self.coordinator.entities[self.attr]

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update()

    def async_set_state(self, state):
        """Set state."""
        if isinstance(state, dict):
            self._vars.update(state)
            
            # 清空现有属性
            self._attr_extra_state_attributes.clear()
            
            # 导入中文显示文本常量
            from .const_display import (
                door_position_map,
                door_suffix_map,
                bool_display_map,
                door_lock_display_map
            )
            
            # 将所有订阅的属性添加到extra_state_attributes
            for attr_name in self.subscribed_attrs:
                if attr_name in state:
                    value = state[attr_name]
                    
                    # 处理属性值，根据属性名转换为不同的友好文本显示
                    if isinstance(value, bool):
                        # 检查属性名是否是"door_status"（整体车门状态）
                        if attr_name == "door_status":
                            # 整体车门状态：表示车门是否打开，显示"开"/"关"
                            value = bool_display_map[value]
                        # 检查属性名是否包含"open"，用于区分车门开关状态
                        elif "open" in attr_name.lower():
                            # 车门开关状态：显示"开"/"关"
                            value = bool_display_map[value]
                        # 检查属性名是否是车门锁定状态（doorX_status）
                        elif attr_name in ["door1_status", "door2_status", "door3_status", "door4_status"]:
                            # 车门锁定状态：反转显示，0为锁定，1为解锁
                            value = door_lock_display_map[value]
                        # 检查属性名是否包含"lock"，用于区分车门锁定状态
                        elif "lock" in attr_name.lower():
                            # 车门锁定状态：反转显示，0为锁定，1为解锁
                            value = door_lock_display_map[value]
                        else:
                            # 其他布尔值：默认显示"开"/"关"
                            value = bool_display_map[value]
                    
                    # 处理属性名，将其转换为更直观的中文名称
                    display_attr_name = attr_name
                    
                    # 替换车门位置（door1 → 左前）
                    for door, position in door_position_map.items():
                        if door in display_attr_name:
                            display_attr_name = display_attr_name.replace(door, position)
                            break
                    
                    # 优化属性名显示，使其更加直观
                    for suffix, display_suffix in door_suffix_map.items():
                        if suffix in display_attr_name:
                            display_attr_name = display_attr_name.replace(suffix, display_suffix)
                            break
                    
                    # 将属性添加到extra_state_attributes，使用中文属性名
                    self._attr_extra_state_attributes[display_attr_name] = value
            
            # 处理设备追踪器实体的特殊情况
            if self.attr == 'location':
                # 设备追踪器实体：设置状态
                # 设置状态为地址，如果有的话
                if 'address' in state and hasattr(self, '_attr_state'):
                    self._attr_state = state['address']
                
                # 将base_info的属性转移到location实体，如有重复则掠过
                # 从carInfo中获取基本信息
                car_info = self.coordinator.data.get('carInfo', {})
                
                # 基本信息属性映射，与BaseInfoConv保持一致
                # 移除了car_name、color_name和car_image属性，因为这些已经存在于设备追踪器实体的基本属性中
                base_info_attrs = {
                    'car_type_name': 'carTypeName',  # 车型名称
                    'car_year': 'carYear',           # 车型年款
                    'model': 'model',               # model
                    'vin': 'vin',                   # 车辆识别码
                    'car_info_id': 'carInfoId',      # 车辆信息ID
                    'vsn': 'vsn',                   # 车辆序列号
                    'series_code': 'seriesCode',     # 车系代码
                    'purchase_shop_num': 'purchaseShopNum',  # 购买店铺编号
                    'purchase_user_name': 'purchaseUserName',  # 购买人姓名
                    'color_code': 'colorCode',       # 颜色代码
                    'user_id': 'userId',             # 用户ID
                }
                
                # 添加基本信息属性，如有重复则掠过
                for attr_name, car_info_key in base_info_attrs.items():
                    # 只有当属性不存在时才添加，避免覆盖现有属性
                    if attr_name not in self._attr_extra_state_attributes and car_info_key in car_info:
                        self._attr_extra_state_attributes[attr_name] = car_info[car_info_key]
            # 处理地址传感器的特殊情况
            elif self.attr == 'address':
                # 地址传感器：设置状态
                if self.attr in state:
                    # 支持不同类型实体的状态属性
                    value = state[self.attr]
                    if hasattr(self, '_attr_state'):
                        self._attr_state = value
                    if hasattr(self, '_attr_native_value'):
                        self._attr_native_value = value
                
                # 将高德API返回的所有字段作为属性添加到传感器
                if 'gaode_address_detail' in self.coordinator.data:
                    # 清空现有属性
                    self._attr_extra_state_attributes.clear()
                    
                    # 获取高德地址详情
                    gaode_detail = self.coordinator.data['gaode_address_detail']
                    
                    # 添加基本地址信息
                    self._attr_extra_state_attributes.update({
                        'address': gaode_detail.get('formatted_address', ''),
                        'province': gaode_detail.get('province', ''),
                        'city': gaode_detail.get('city', ''),
                        'district': gaode_detail.get('district', ''),
                        'township': gaode_detail.get('township', ''),
                        'street': gaode_detail.get('street', ''),
                        'number': gaode_detail.get('number', ''),
                        'adcode': gaode_detail.get('adcode', ''),
                        'citycode': gaode_detail.get('citycode', ''),
                        'towncode': gaode_detail.get('towncode', ''),
                        'distance': gaode_detail.get('distance', ''),
                        'direction': gaode_detail.get('direction', ''),
                    })
                    
                    # 添加完整的响应数据（可选，根据需要）
                    # self._attr_extra_state_attributes['full_result'] = gaode_detail.get('full_result', {})
                    # self._attr_extra_state_attributes['regeocode'] = gaode_detail.get('regeocode', {})
            else:
                # 普通实体：只设置自身的状态
                if self.attr in state:
                    # 支持不同类型实体的状态属性
                    value = state[self.attr]
                    # 尝试同时设置不同的状态属性，确保所有实体类型都能正确显示
                    if hasattr(self, '_attr_state'):
                        self._attr_state = value
                    if hasattr(self, '_attr_native_value'):
                        self._attr_native_value = value
        else:
            self._vars[self.attr] = state
            # 支持不同类型实体的状态属性
            value = state
            if hasattr(self, '_attr_state'):
                self._attr_state = value
            if hasattr(self, '_attr_native_value'):
                self._attr_native_value = value
