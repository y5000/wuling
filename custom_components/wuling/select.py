from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.components.select import (
    DOMAIN as ENTITY_DOMAIN,
    SelectEntity as BaseEntity,
)

from .entities import XEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[entry.entry_id]['coordinator']
    for conv in coordinator.converters:
        # 只检查domain，不检查parent，允许子实体被添加
        if conv.domain != ENTITY_DOMAIN:
            continue
        async_add_entities([SelectEntity(coordinator, conv)])


class SelectEntity(XEntity, BaseEntity):
    def __init__(self, coordinator, conv):
        super().__init__(coordinator, conv)
        # 初始化选项列表为空列表，避免AttributeError
        self._attr_options = []
        # 从协调器获取初始选中值，确保重启后能恢复
        self._attr_current_option = getattr(coordinator, 'selected_mobile_device', "")
    
    @callback
    def async_set_state(self, data: dict):
        super().async_set_state(data)
        if self.attr in data:
            self._attr_current_option = data[self.attr]
        if "options" in data:
            self._attr_options = data["options"]
    
    @property
    def current_option(self):
        """获取当前选项值"""
        # 返回实际的选项值，而不是友好名称，让Home Assistant能够正确保存
        return self._attr_current_option
    
    @property
    def option_labels(self):
        """获取选项的友好名称映射"""
        if hasattr(self.coordinator, 'mobile_device_labels'):
            return self.coordinator.mobile_device_labels
        return {}
    
    @property
    def translated_options(self):
        """获取带友好名称的选项列表，用于显示"""
        return [self.option_labels.get(opt, opt) for opt in self._attr_options]
    
    @property
    def options(self):
        """获取选项列表"""
        return self._attr_options
    
    @property
    def state(self):
        """获取实体状态，返回当前选项值，用于Home Assistant保存"""
        return self._attr_current_option
    
    async def async_select_option(self, option: str) -> None:
        """选择选项"""
        # conv.encode() 方法不返回协程对象，不需要使用 await
        self.conv.encode(self.coordinator, {}, option)
        # 更新实体状态
        self._attr_current_option = option
        self.async_write_ha_state()
