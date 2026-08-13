"""Config flow: chọn kết nối qua ESP32 TCP bridge hoặc RS232-USB trực tiếp."""
from __future__ import annotations

import logging

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL,
    CONF_CONNECTION_TYPE, CONF_SERIAL_PORT, CONF_BAUD_RATE,
    CONF_DATA_BITS, CONF_PARITY, CONF_STOP_BITS,
    CONNECTION_TCP, CONNECTION_SERIAL, DEFAULT_BAUD_RATE, DEFAULT_SERIAL_PORT,
    DEFAULT_DATA_BITS, DEFAULT_PARITY, DEFAULT_STOP_BITS,
    STANDARD_BAUD_RATES, PARITY_OPTIONS, DATA_BITS_OPTIONS, STOP_BITS_OPTIONS,
)
from .coordinator import InverterTcpClient, InverterSerialClient


def _serial_schema(defaults: dict) -> vol.Schema:
    """Schema dùng chung cho cả bước setup ban đầu lẫn Options Flow."""
    return vol.Schema(
        {
            vol.Required(CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, DEFAULT_SERIAL_PORT)): str,
            vol.Optional(
                CONF_BAUD_RATE, default=defaults.get(CONF_BAUD_RATE, DEFAULT_BAUD_RATE)
            ): vol.In(STANDARD_BAUD_RATES),
            vol.Optional(
                CONF_DATA_BITS, default=defaults.get(CONF_DATA_BITS, DEFAULT_DATA_BITS)
            ): vol.In(DATA_BITS_OPTIONS),
            vol.Optional(
                CONF_PARITY, default=defaults.get(CONF_PARITY, DEFAULT_PARITY)
            ): vol.In(PARITY_OPTIONS),
            vol.Optional(
                CONF_STOP_BITS, default=str(defaults.get(CONF_STOP_BITS, DEFAULT_STOP_BITS))
            ): vol.In(STOP_BITS_OPTIONS),
            vol.Optional(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
        }
    )


class HsMsMsxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Bước đầu: chọn kiểu kết nối."""
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == CONNECTION_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_tcp()

        schema = vol.Schema(
            {
                vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TCP): vol.In(
                    {
                        CONNECTION_TCP: "ESP32 TCP bridge (WiFi)",
                        CONNECTION_SERIAL: "RS232-USB cắm trực tiếp vào máy chạy HA",
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_tcp(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: CONNECTION_TCP, **user_input}
            client = InverterTcpClient(user_input[CONF_HOST], user_input[CONF_PORT])
            try:
                await client.fetch_all()
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Không lấy được dữ liệu từ inverter: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Sumry Inverter {user_input[CONF_HOST]}", data=data
                )
            finally:
                await client.async_close()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )
        return self.async_show_form(step_id="tcp", data_schema=schema, errors=errors)

    async def async_step_serial(self, user_input=None):
        errors = {}
        if user_input is not None:
            stop_bits = float(user_input[CONF_STOP_BITS])
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_SERIAL,
                **user_input,
                CONF_STOP_BITS: stop_bits,  # lưu dạng số (1, 1.5, 2) thay vì chuỗi UI
            }
            client = InverterSerialClient(
                user_input[CONF_SERIAL_PORT],
                user_input[CONF_BAUD_RATE],
                user_input[CONF_DATA_BITS],
                user_input[CONF_PARITY],
                stop_bits,
            )
            try:
                await client.fetch_all()
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Không đọc được inverter qua %s: %s", user_input[CONF_SERIAL_PORT], err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Sumry Inverter {user_input[CONF_SERIAL_PORT]}", data=data
                )
            finally:
                await client.async_close()

        schema = _serial_schema({})
        return self.async_show_form(step_id="serial", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HsMsMsxOptionsFlow(config_entry)


class HsMsMsxOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self._is_serial = config_entry.data.get(CONF_CONNECTION_TYPE) == CONNECTION_SERIAL

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            data = dict(user_input)
            if self._is_serial:
                data[CONF_STOP_BITS] = float(user_input[CONF_STOP_BITS])
            return self.async_create_entry(title="", data=data)

        # Baud rate/data bits/parity/stop bits qua TCP là do firmware ESP32
        # quyết định (biên dịch cứng trong yaml UART), HA không đổi được từ
        # xa qua đường TCP passthrough -> chỉ hiện các trường này khi kết
        # nối trực tiếp qua serial.
        if self._is_serial:
            current = {**self.config_entry.data, **self.config_entry.options}
            schema = _serial_schema(current)
        else:
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        ),
                    ): int,
                }
            )

        return self.async_show_form(step_id="init", data_schema=schema)
