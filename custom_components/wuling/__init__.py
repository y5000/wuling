import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, SUPPORTED_PLATFORMS, _LOGGER
from .coordinator import StateCoordinator
from .entities import XEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(entry.entry_id, {})
    hass.data[entry.entry_id].setdefault('entities', {})
    coordinator = StateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.check_auth()
    hass.data[entry.entry_id]['coordinator'] = coordinator

    hass.services.async_register(
        DOMAIN, 'update_status', coordinator.update_from_service,
        schema=vol.Schema({}, extra=vol.ALLOW_EXTRA),
        supports_response=SupportsResponse.OPTIONAL,
    )

    await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项并释放资源"""
    # 取消平台设置
    unload_ok = await hass.config_entries.async_unload_platforms(entry, SUPPORTED_PLATFORMS)
    
    # 取消注册服务
    hass.services.async_remove(DOMAIN, 'update_status')
    
    # 清理数据
    if entry.entry_id in hass.data:
        # 取消协调器的更新
        coordinator = hass.data[entry.entry_id].get('coordinator')
        if coordinator:
            await coordinator.async_shutdown()
        
        # 清理实体
        entities = hass.data[entry.entry_id].get('entities', {})
        for entity in entities.values():
            if hasattr(entity, 'async_remove'):
                await entity.async_remove()
        
        # 删除配置项数据
        del hass.data[entry.entry_id]
    
    return unload_ok


# 导出类和常量
__all__ = [
    'DOMAIN',
    'StateCoordinator',
    'XEntity',
    'async_setup_entry',
    'async_unload_entry',
]
