from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfLength,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfElectricPotential,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .converters import (
    BinarySensorConv,
    ButtonConv,
    Converter,
    MapSensorConv,
    NumberSensorConv,
    SensorConv,
    BoolConv,
    MapConv,
    NumberConv,
    TimeStampConv,
    SelectConv,
    TireTempConv,
)


def create_converters():
    """创建所有传感器转换器"""
    converters = [
        # =========================================
        # 1. 电池系统传感器
        # =========================================
        NumberSensorConv('battery', prop='carStatus.batterySoc').with_option({
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.BATTERY,
            'unit_of_measurement': PERCENTAGE,
        }),
        NumberSensorConv('battery_temp', prop='carStatus.batAvgTemp').with_option({
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.TEMPERATURE,
            'unit_of_measurement': UnitOfTemperature.CELSIUS,
        }),
        NumberSensorConv('battery_voltage', prop='carStatus.voltage', ignore_zero=True).with_option({
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.VOLTAGE,
            'unit_of_measurement': UnitOfElectricPotential.VOLT,
        }),
        NumberSensorConv('battery_health', prop='carStatus.batHealth').with_option({
            'icon': 'mdi:battery-heart-variant',
            'state_class': SensorStateClass.MEASUREMENT,
            'entity_category': EntityCategory.DIAGNOSTIC,
            'unit_of_measurement': PERCENTAGE,
        }),
        SensorConv('battery_status', prop='carStatus.batteryStatus').with_option({
            'icon': 'mdi:battery-unknown',
        }),
        NumberSensorConv('small_battery_voltage', prop='carStatus.lowBatVol', ignore_zero=True).with_option({
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.VOLTAGE,
            'unit_of_measurement': UnitOfElectricPotential.VOLT,
        }),
        
        # =========================================
        # 2. 里程系统传感器
        # =========================================
        NumberSensorConv('total_mileage', prop='carStatus.mileage').with_option({
            'icon': 'mdi:counter',
            'state_class': SensorStateClass.TOTAL,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('left_mileage', prop='carStatus.leftMileage').with_option({
            'icon': 'mdi:lightning-bolt',
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('left_mileage_oil', prop='carStatus.oilLeftMileage').with_option({
            'icon': 'mdi:water',
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('yesterday_mileage', prop='yesterdayMileage.trip', ignore_zero=True).with_option({
            'icon': 'mdi:clock-outline',
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('avgFuel', prop='carStatus.avgFuel').with_option({
            'icon': 'mdi:water',
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('total_hev_mileage', prop='carStatus.hybridMileage', ignore_zero=True).with_option({
            'icon': 'mdi:water',
            'state_class': SensorStateClass.MEASUREMENT,
            'device_class': SensorDeviceClass.DISTANCE,
            'unit_of_measurement': UnitOfLength.KILOMETERS,
        }),
        NumberSensorConv('oil_level', prop='carStatus.leftFuel').with_option({
            'icon': 'mdi:water-percent',
            'state_class': SensorStateClass.MEASUREMENT,
            'unit_of_measurement': PERCENTAGE,
        }),
        
        # =========================================
        # 3. 门锁系统传感器
        # =========================================
        BoolConv('door_lock', Platform.LOCK, prop='carStatus.doorLockStatus', reverse=True).with_option({
            'icon': 'mdi:car-door-lock',
        }),
        BinarySensorConv('door1_lock_status', prop='carStatus.door1LockStatus', parent='door_lock').with_option({
            'device_class': BinarySensorDeviceClass.LOCK,
        }),
        BinarySensorConv('door2_lock_status', prop='carStatus.door2LockStatus', parent='door_lock').with_option({
            'device_class': BinarySensorDeviceClass.LOCK,
        }),
        BinarySensorConv('door3_lock_status', prop='carStatus.door3LockStatus', parent='door_lock').with_option({
            'device_class': BinarySensorDeviceClass.LOCK,
        }),
        BinarySensorConv('door4_lock_status', prop='carStatus.door4LockStatus', parent='door_lock').with_option({
            'device_class': BinarySensorDeviceClass.LOCK,
        }),
        BinarySensorConv('tail_door_lock_status', prop='carStatus.tailDoorLockStatus', parent='door_lock').with_option({
            'icon': 'mdi:car-back',
            'device_class': BinarySensorDeviceClass.LOCK,
        }),
        
        # =========================================
        # 4. 车门/车窗系统传感器
        # =========================================
        BinarySensorConv('door_status', prop='carStatus.doorOpenStatus').with_option({
            'icon': 'mdi:car-door',
            'device_class': BinarySensorDeviceClass.DOOR,
        }),
        BinarySensorConv('door1_open_status', prop='carStatus.door1OpenStatus', parent='door_status').with_option({
            'device_class': BinarySensorDeviceClass.DOOR,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('door2_open_status', prop='carStatus.door2OpenStatus', parent='door_status').with_option({
            'device_class': BinarySensorDeviceClass.DOOR,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('door3_open_status', prop='carStatus.door3OpenStatus', parent='door_status').with_option({
            'device_class': BinarySensorDeviceClass.DOOR,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('door4_open_status', prop='carStatus.door4OpenStatus', parent='door_status').with_option({
            'device_class': BinarySensorDeviceClass.DOOR,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('tail_door_open_status', prop='carStatus.tailDoorOpenStatus', parent='door_status').with_option({
            'icon': 'mdi:car-back',
            'device_class': BinarySensorDeviceClass.DOOR,
        }),
        
        # 车窗系统传感器
        BinarySensorConv('window_status', prop='carStatus.windowOpenStatus').with_option({
            'icon': 'mdi:dock-window',
            'device_class': BinarySensorDeviceClass.WINDOW,
        }),
        BinarySensorConv('window1_status', prop='carStatus.window1OpenStatus', parent='window_status').with_option({
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window2_status', prop='carStatus.window2OpenStatus', parent='window_status').with_option({
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window3_status', prop='carStatus.window3OpenStatus', parent='window_status').with_option({
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window4_status', prop='carStatus.window4OpenStatus', parent='window_status').with_option({
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window1_open_degree', prop='carStatus.window1OpenDegree', parent='window_status').with_option({
            'icon': 'mdi:window-open-variant',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window2_open_degree', prop='carStatus.window2OpenDegree', parent='window_status').with_option({
            'icon': 'mdi:window-open-variant',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window3_open_degree', prop='carStatus.window3OpenDegree', parent='window_status').with_option({
            'icon': 'mdi:window-open-variant',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'entity_registry_enabled_default': False,
        }),
        BinarySensorConv('window4_open_degree', prop='carStatus.window4OpenDegree', parent='window_status').with_option({
            'icon': 'mdi:window-open-variant',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'entity_registry_enabled_default': False,
        }),
        
        # =========================================
        # 5. 灯光系统传感器
        # =========================================
        BinarySensorConv('front_fog_light', prop='carStatus.frontFogLight').with_option({
            'icon': 'mdi:car-light-fog',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        BinarySensorConv('left_turn_light', prop='carStatus.leftTurnLight').with_option({
            'icon': 'mdi:car-arrow-left',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        BinarySensorConv('position_light', prop='carStatus.positionLight').with_option({
            'icon': 'mdi:car-parking-lights',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        BinarySensorConv('right_turn_light', prop='carStatus.rightTurnLight').with_option({
            'icon': 'mdi:car-arrow-right',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        BinarySensorConv('dip_head_light', prop='carStatus.dipHeadLight').with_option({
            'icon': 'mdi:car-light-high',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        BinarySensorConv('low_beam_light', prop='carStatus.lowBeamLight').with_option({
            'icon': 'mdi:car-light-dimmed',
            'device_class': BinarySensorDeviceClass.LIGHT,
        }),
        
        # =========================================
        # 6. 充电系统传感器
        # =========================================
        BinarySensorConv('charging', prop='carStatus.charging').with_option({
            'device_class': BinarySensorDeviceClass.BATTERY_CHARGING,
        }),
        BinarySensorConv('plugging', prop='carStatus.vecChrgingSts').with_option({
            'device_class': BinarySensorDeviceClass.PLUG,
        }),
        
        # =========================================
        # 7. 发动机/动力系统传感器
        # =========================================
        MapSensorConv('key_status', prop='carStatus.keyStatus', map={
            '0': '无钥匙',
            '1': '已连接',
            '2': '已启动',
        }).with_option({
            'icon': 'mdi:key',
        }),
        MapSensorConv('gear_status', prop='carStatus.autoGearStatus', map={
            '10': 'P',
            '12': 'D',
            '13': 'N',
            '14': 'R',
        }).with_option({
            'icon': 'mdi:car-shift-pattern',
        }),
        BinarySensorConv('engine_power', prop='checkStatus.enginePow', reverse=True).with_option({
            'icon': 'mdi:turbine',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('engine_temp', prop='checkStatus.engineTemp', reverse=True).with_option({
            'icon': 'mdi:coolant-temperature',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('abs', prop='checkStatus.absio').with_option({
            'icon': 'mdi:car-brake-abs',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('power_steering', prop='checkStatus.pwrStrIo').with_option({
            'icon': 'mdi:steering',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('battery_voltage_check', prop='checkStatus.batVol', reverse=True).with_option({
            'icon': 'mdi:car-battery',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('battery_temp_check', prop='checkStatus.batTemp', reverse=True).with_option({
            'icon': 'mdi:thermometer',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('battery_score', prop='checkStatus.batScore', reverse=True).with_option({
            'icon': 'mdi:battery-heart-variant',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('engine_score', prop='checkStatus.engineScore', reverse=True).with_option({
            'icon': 'mdi:engine',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        SensorConv('cdu_state', prop='checkStatus.cduState').with_option({
            'icon': 'mdi:eye',
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        
        # =========================================
        # 8. 空调系统传感器
        # =========================================
        MapConv('ac', domain=Platform.CLIMATE, prop='carStatus.acStatus', map={
            '0': 'off',
            '1': 'cool',
            '2': 'heat',
        }).with_option({
            'icon': 'mdi:air-conditioner',
        }),
        NumberSensorConv('current_temperature', prop='carStatus.invActTemp', parent='ac').with_option({
            'entity_registry_enabled_default': False,
        }),
        NumberSensorConv('target_temperature', prop='carStatus.accCntTemp', parent='ac').with_option({
            'entity_registry_enabled_default': False,
        }),
        
        # =========================================
        # 9. 轮胎系统传感器
        # =========================================
        # 胎压传感器 - 按照用户要求的顺序排列：左前 → 右前 → 左后 → 右后
        # 左前胎压
        NumberSensorConv('tire_pressure_lf', prop='tirePressure.lfTirPrsVal', ratio=1, precision=2).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': SensorDeviceClass.PRESSURE,
            'unit_of_measurement': 'bar',
        }),
        # 左前温度
        NumberSensorConv('tire_temp_lf', prop=None, precision=1).with_option({
            'icon': 'mdi:tire',
            'device_class': SensorDeviceClass.TEMPERATURE,
            'unit_of_measurement': UnitOfTemperature.CELSIUS,
        }),
        # 右前胎压
        NumberSensorConv('tire_pressure_rf', prop='tirePressure.rfTirPrVal', ratio=1, precision=2).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': SensorDeviceClass.PRESSURE,
            'unit_of_measurement': 'bar',
        }),
        # 右前温度
        NumberSensorConv('tire_temp_rf', prop=None, precision=1).with_option({
            'icon': 'mdi:tire',
            'device_class': SensorDeviceClass.TEMPERATURE,
            'unit_of_measurement': UnitOfTemperature.CELSIUS,
        }),
        # 左后胎压
        NumberSensorConv('tire_pressure_lr', prop='tirePressure.lrTirPrVal', ratio=1, precision=2).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': SensorDeviceClass.PRESSURE,
            'unit_of_measurement': 'bar',
        }),
        # 左后温度
        NumberSensorConv('tire_temp_lr', prop=None, precision=1).with_option({
            'icon': 'mdi:tire',
            'device_class': SensorDeviceClass.TEMPERATURE,
            'unit_of_measurement': UnitOfTemperature.CELSIUS,
        }),
        # 右后胎压
        NumberSensorConv('tire_pressure_rr', prop='tirePressure.rrTirPrVal', ratio=1, precision=2).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': SensorDeviceClass.PRESSURE,
            'unit_of_measurement': 'bar',
        }),
        # 右后温度
        NumberSensorConv('tire_temp_rr', prop=None, precision=1).with_option({
            'icon': 'mdi:tire',
            'device_class': SensorDeviceClass.TEMPERATURE,
            'unit_of_measurement': UnitOfTemperature.CELSIUS,
        }),
        
        # 胎压诊断传感器 - 按照相同顺序排列：左前 → 右前 → 左后 → 右后
        # 左前胎压状态
        BinarySensorConv('tire_pressure_lf_status', prop='tirePressure.lfTirPrStat', reverse=False).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        # 右前胎压状态
        BinarySensorConv('tire_pressure_rf_status', prop='tirePressure.rfTirPrStat', reverse=False).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        # 左后胎压状态
        BinarySensorConv('tire_pressure_lr_status', prop='tirePressure.lrTirPrStat', reverse=False).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        # 右后胎压状态
        BinarySensorConv('tire_pressure_rr_status', prop='tirePressure.rrTirPrStat', reverse=False).with_option({
            'icon': 'mdi:car-tire-alert',
            'device_class': BinarySensorDeviceClass.PROBLEM,
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        
        # 轮胎温度分配转换器 - 隐藏实体，只在后台执行转换功能
        TireTempConv('tire_temp_converter', prop='tirePressure.locTirTemp').with_option({
            'entity_category': EntityCategory.DIAGNOSTIC,
            # 添加内部使用标记，防止实体被添加到Home Assistant
            '__internal_use': True,
        }),
        
        # =========================================
        # 10. 车辆基本信息传感器
        # =========================================
        # 其他基本信息传感器
        NumberSensorConv('car_owner_day', prop='carInfo.carOwnerDay').with_option({
            'icon': 'mdi:calendar-check',
            'state_class': SensorStateClass.TOTAL,
        }),
        BinarySensorConv('has_more_car', prop='carInfo.hasMoreCar').with_option({
            'icon': 'mdi:car-multiple',
            'entity_category': EntityCategory.DIAGNOSTIC,
        }),
        BinarySensorConv('finish_bind', prop='carInfo.finishBind').with_option({
            'icon': 'mdi:check-circle',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'device_class': BinarySensorDeviceClass.OPENING,
        }),
        BinarySensorConv('is_auth_identity', prop='carInfo.isAuthIdentity').with_option({
            'icon': 'mdi:shield-account',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'device_class': BinarySensorDeviceClass.SAFETY,
        }),
        BinarySensorConv('support_mqtt', prop='carInfo.supportMqtt').with_option({
            'icon': 'mdi:wifi',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'device_class': BinarySensorDeviceClass.OPENING,
        }),
        BinarySensorConv('support_hybrid_mileage', prop='carInfo.supportHybridMileage').with_option({
            'icon': 'mdi:gauge',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'device_class': BinarySensorDeviceClass.OPENING,
        }),
        BinarySensorConv('support_auto_air', prop='carInfo.supportAutoAir').with_option({
            'icon': 'mdi:air-conditioner',
            'entity_category': EntityCategory.DIAGNOSTIC,
            'device_class': BinarySensorDeviceClass.OPENING,
        }),
        
        # =========================================
        # 11. 设备追踪器
        # =========================================
        Converter('location', Platform.DEVICE_TRACKER).with_option({
            'icon': 'mdi:car',
        }),
        NumberSensorConv('latitude', prop='carStatus.latitude', parent='location', precision=6).with_option({
            'entity_registry_enabled_default': False,
        }),
        NumberSensorConv('longitude', prop='carStatus.longitude', parent='location', precision=6).with_option({
            'entity_registry_enabled_default': False,
        }),
        NumberSensorConv('battery_level', prop='carStatus.batterySoc', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('vin', prop='carInfo.vin', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('name', prop='carInfo.carName', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('plate', prop='carInfo.carPlate', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('color', prop='carInfo.colorName', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('entity_picture', prop='carInfo.image', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        SensorConv('collect_time', prop='carStatus.collectTime', parent='location').with_option({
            'entity_registry_enabled_default': False,
        }),
        # 地址传感器 - 从高德API获取的地址名称
        SensorConv('address', prop='address', parent='location').with_option({
            'icon': 'mdi:map-marker',
        }),
        
        # =========================================
        # 12. 按钮设备
        # =========================================
        ButtonConv('search_car', press='async_search_car').with_option({
            'icon': 'mdi:car-search',
        }),
        ButtonConv('auth_start', press='async_auth_start').with_option({
            'icon': 'mdi:engine',
        }),
        
        # =========================================
        # 13. 设置系统
        # =========================================
        # API刷新速率设置
        NumberConv('basic_api_refresh_rate', domain='number').with_option({
            'icon': 'mdi:refresh',
            'min_value': 1,
            'max_value': 120,
            'step': 1,
            'unit_of_measurement': 's',
            'mode': 'box',
        }),
        NumberConv('other_api_refresh_rate', domain='number').with_option({
            'icon': 'mdi:cloud-refresh-variant',
            'min_value': 10,
            'max_value': 3600,
            'step': 10,
            'unit_of_measurement': 's',
            'mode': 'box',
        }),
        
        # 调试模式开关
        BoolConv('debug_mode', domain=Platform.SWITCH).with_option({
            'icon': 'mdi:bug-outline',
            'device_class': 'switch',
        }),
        
        # 发送消息选择设备
        SelectConv('send_message_device', domain=Platform.SELECT).with_option({
            'icon': 'mdi:message-text-outline',
            'device_class': 'select',
        }),
        
        # 手动刷新地址按钮
        ButtonConv('refresh_address', press='async_refresh_address').with_option({
            'icon': 'mdi:map-refresh',
        }),
        
        # =========================================
        # 14. API时间戳传感器
        # =========================================
        TimeStampConv('basic_api_timestamp', prop='basic_api_timestamp').with_option({
            'icon': 'mdi:clock-outline',
            'device_class': SensorDeviceClass.TIMESTAMP,
        }),
        TimeStampConv('check_api_timestamp', prop='check_api_timestamp').with_option({
            'icon': 'mdi:clock-outline',
            'device_class': SensorDeviceClass.TIMESTAMP,
        }),
        TimeStampConv('tire_api_timestamp', prop='tire_api_timestamp').with_option({
            'icon': 'mdi:clock-outline',
            'device_class': SensorDeviceClass.TIMESTAMP,
        }),
        TimeStampConv('yesterday_mileage_api_timestamp', prop='yesterday_mileage_api_timestamp').with_option({
            'icon': 'mdi:clock-outline',
            'device_class': SensorDeviceClass.TIMESTAMP,
        }),
        
        # 车门未关通知时间传感器
        TimeStampConv('last_door_notification_time', prop='last_door_notification_time').with_option({
            'icon': 'mdi:bell-outline',
            'device_class': SensorDeviceClass.TIMESTAMP,
        })
    ]
    return converters
