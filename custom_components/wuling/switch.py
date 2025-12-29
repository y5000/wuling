from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.components.switch import (
    DOMAIN as ENTITY_DOMAIN,
    SwitchEntity as BaseEntity,
)

from .entities import XEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[entry.entry_id]['coordinator']
    for conv in coordinator.converters:
        # 只检查domain，不检查parent，允许子实体被添加
        if conv.domain != ENTITY_DOMAIN:
            continue
        async_add_entities([SwitchEntity(coordinator, conv)])


class SwitchEntity(XEntity, BaseEntity):
    @callback
    def async_set_state(self, data: dict):
        super().async_set_state(data)
        if self.attr in data:
            self._attr_is_on = data[self.attr]
    
    async def async_turn_on(self, **kwargs):
        """打开开关"""
        # conv.encode() 方法不返回协程对象，不需要使用 await
        self.conv.encode(self.coordinator, {}, True)
        # 更新实体状态
        self._attr_is_on = True
        self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs):
        """关闭开关"""
        # conv.encode() 方法不返回协程对象，不需要使用 await
        self.conv.encode(self.coordinator, {}, False)
        # 更新实体状态
        self._attr_is_on = False
        self.async_write_ha_state()
