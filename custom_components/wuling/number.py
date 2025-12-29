from __future__ import annotations

import logging

from homeassistant.components.number import (
    DOMAIN as ENTITY_DOMAIN,
    NumberEntity as BaseEntity,
)
from .entities import XEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[entry.entry_id]['coordinator']
    for conv in coordinator.converters:
        # 只检查domain，不检查parent，允许子实体被添加
        if conv.domain != ENTITY_DOMAIN:
            continue
        async_add_entities([NumberEntity(coordinator, conv)])


class NumberEntity(XEntity, BaseEntity):
    def __init__(self, coordinator, conv):
        super().__init__(coordinator, conv)
        self._attr_native_min_value = self._option.get('min_value', 10)
        self._attr_native_max_value = self._option.get('max_value', 3600)
        self._attr_native_step = self._option.get('step', 10)
        self._attr_native_unit_of_measurement = self._option.get('unit_of_measurement', 's')
        self._attr_mode = self._option.get('mode', 'box')

    @property
    def native_value(self):
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        # 直接await encode方法返回的协程对象
        await self.conv.encode(self.coordinator, {}, value)
        # 更新实体状态
        self._attr_native_value = value
        self.async_write_ha_state()