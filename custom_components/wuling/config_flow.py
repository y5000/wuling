import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.core import callback
from .const import DOMAIN, TITLE, CONF_AMAP_KEY


def get_schemas(defaults):
    return vol.Schema({
        vol.Required(CONF_ACCESS_TOKEN, default=defaults.get(CONF_ACCESS_TOKEN)): str,
        vol.Required(CONF_CLIENT_ID, default=defaults.get(CONF_CLIENT_ID)): str,
        vol.Required(CONF_CLIENT_SECRET, default=defaults.get(CONF_CLIENT_SECRET)): str,
        vol.Optional(CONF_AMAP_KEY, default=defaults.get(CONF_AMAP_KEY, '')): str,
    })


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()

    async def async_step_user(self, user_input):
        if user_input is None:
            user_input = {}
        # 当用户提交配置时，保存所有字段，包括空字段
        if user_input:
            return self.async_create_entry(title=TITLE, data=user_input)

        self.context['tip'] = '请抓包获取以下参数'
        return self.async_show_form(
            step_id='user',
            data_schema=get_schemas(user_input),
            description_placeholders={'tip': self.context.pop('tip', '')},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is None:
            user_input = {}
        # 当用户提交配置时，保存所有字段，包括空字段
        if user_input:
            # 更新配置条目
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, **user_input}
            )
            return self.async_create_entry(title='', data=user_input)
        defaults = {
            **self.config_entry.data,
            **self.config_entry.options,
            **user_input,
        }
        return self.async_show_form(
            step_id='init',
            data_schema=get_schemas(defaults),
            description_placeholders={'tip': self.context.pop('tip', '')},
        )
