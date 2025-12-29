import logging
import random
import string
from datetime import timedelta

from homeassistant.const import (
    Platform,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    PERCENTAGE,
    UnitOfLength,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfElectricPotential,
)

# 高德API配置
CONF_AMAP_KEY = 'amap_key'  # 高德地图API密钥，用于备用定位服务

DOMAIN = 'wuling'
TITLE = '五菱汽车'
API_BASE = 'https://openapi.baojun.net/junApi/sgmw'

SUPPORTED_PLATFORMS = [
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.LOCK,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.NUMBER,
    Platform.SELECT,
]

# Entity category constants
DOOR_WINDOW_ENTITIES = {
    'window_status', 'window1_status', 'window2_status', 'window3_status', 'window4_status',
    'window1_open_degree', 'window2_open_degree', 'window3_open_degree', 'window4_open_degree',
    'door_status', 'door1_status', 'door2_status', 'door3_status', 'door4_status',
    'door1_locked', 'door2_locked', 'door3_locked', 'door4_locked',
    'door1_open_status', 'door2_open_status', 'door3_open_status', 'door4_open_status',
    'door1_lock_status', 'door2_lock_status', 'door3_lock_status', 'door4_lock_status',
    'tail_door_status', 'tail_door_open_status', 'tail_door_lock_status',
    'left_sliding_door_status', 'right_sliding_door_status'
}

LIGHT_ENTITIES = {
    'front_fog_light', 'left_turn_light', 'position_light', 'right_turn_light',
    'dip_head_light', 'low_beam_light'
}

BASIC_INFO_ENTITIES = {
    'car_owner_day', 'has_more_car', 'finish_bind', 'is_auth_identity', 
    'support_mqtt', 'support_hybrid_mileage', 'support_auto_air'
}

# 轮胎系统实体集合
TIRE_ENTITIES = {
    'tire_temp_lf', 'tire_temp_rf', 'tire_temp_lr', 'tire_temp_rr',
    'tire_pressure_lf', 'tire_pressure_rf', 'tire_pressure_lr', 'tire_pressure_rr',
    'tire_pressure_lf_status', 'tire_pressure_rf_status', 'tire_pressure_lr_status', 'tire_pressure_rr_status'
}

# 设置系统实体集合
SETTINGS_ENTITIES = {
    'basic_api_refresh_rate',
    'other_api_refresh_rate',
    'debug_mode',
    'send_message_device',
    'refresh_address',  # 手动刷新地址按钮
    'basic_api_timestamp',
    'check_api_timestamp',
    'tire_api_timestamp',
    'yesterday_mileage_api_timestamp',
    'last_door_notification_time'  # 车门未关通知时间
}

_LOGGER = logging.getLogger(__name__)

# API configuration
sgmwnonce = ''.join(random.choice(string.ascii_letters) for _ in range(10))
sgmwappcode = 'sgmw_llb'
sgmwappversion = '1656'
sgmwsystem = 'android'
sgmwsystemversion = '10'
