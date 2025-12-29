from __future__ import annotations

import logging

from homeassistant.components.button import (
    DOMAIN as ENTITY_DOMAIN,
    ButtonEntity as BaseEntity,
)
from .entities import XEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    attrs = []
    coordinator = hass.data[entry.entry_id]['coordinator']
    for conv in coordinator.converters:
        # 只检查domain，不检查parent，允许子实体被添加
        if conv.domain != ENTITY_DOMAIN:
            continue
        attrs.append(conv.attr)
        async_add_entities([ButtonEntity(coordinator, conv)])
    _LOGGER.info('async_setup_entry: %s', [ENTITY_DOMAIN, attrs])


class ButtonEntity(XEntity, BaseEntity):
    async def async_press(self):
        """Press the button."""
        fun = self.conv.encode(self.coordinator, {}, None)
        if fun and callable(fun):
            res = await fun() or {}
            self._attr_extra_state_attributes.update(res)
