"""Select entities: các ngưỡng điện áp ắc-quy dạng danh sách lựa chọn."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# key -> (tên hiển thị, prefix lệnh, min, max, step)
# Giữ nguyên step theo number.py cũ:
# PBCV/PBDV = 0.5V
# PSDV/PCVV/PBFT = 0.1V
SELECT_DEFS = {
    "battery_recharge_voltage": ("Điện Áp Chuyển Nguồn", "PBCV", 22.0, 25.5, 0.5),
    "battery_redischarge_voltage": ("Điện Áp Xả Tải", "PBDV", 24.0, 29.0, 0.5),
    "battery_cutoff_voltage": ("Điện Áp Tắt Máy", "PSDV", 20.0, 24.0, 0.1),
    "battery_cv_voltage": ("Điện Áp Đầy Pin", "PCVV", 24.0, 29.2, 0.1),
    "battery_float_voltage": ("Điện Áp Sạc Thả Nổi", "PBFT", 24.0, 29.2, 0.1),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InverterVoltageSelect(
            coordinator, entry, key, name, prefix, vmin, vmax, step
        )
        for key, (name, prefix, vmin, vmax, step) in SELECT_DEFS.items()
    ]
    async_add_entities(entities)


# key trong coordinator.data (từ QPIRI) tương ứng với mỗi select
SELECT_DATA_KEY = {
    "battery_recharge_voltage": "battery_recharge_voltage",
    "battery_redischarge_voltage": "battery_redischarge_voltage",
    "battery_cutoff_voltage": "battery_under_voltage",
    "battery_cv_voltage": "battery_cv_voltage",
    "battery_float_voltage": "battery_float_voltage",
}


def make_options(vmin: float, vmax: float, step: float) -> list[str]:
    """Tạo danh sách điện áp theo đúng step của number cũ."""
    count = round((vmax - vmin) / step)
    return [f"{vmin + i * step:.1f}" for i in range(count + 1)]


class InverterVoltageSelect(CoordinatorEntity, SelectEntity):
    """Select đọc giá trị thật từ QPIRI và gửi lệnh điện áp khi thay đổi."""

    def __init__(
        self,
        coordinator,
        entry,
        key: str,
        name: str,
        cmd_prefix: str,
        vmin: float,
        vmax: float,
        step: float,
    ):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._cmd_prefix = cmd_prefix
        self._data_key = SELECT_DATA_KEY.get(key)
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_unique_id = f"{entry.entry_id}_select_{key}"
        self._attr_options = make_options(vmin, vmax, step)
        self._optimistic_override: float | None = None

    @property
    def current_option(self) -> str | None:
        if self._data_key:
            value = self.coordinator.data.get(self._data_key)
            if value is not None:
                self._optimistic_override = None
                try:
                    value = float(value)
                    option = f"{value:.1f}"
                    if option in self._attr_options:
                        return option
                except (TypeError, ValueError):
                    pass

        if self._optimistic_override is not None:
            option = f"{self._optimistic_override:.1f}"
            if option in self._attr_options:
                return option

        return None

    async def async_select_option(self, option: str) -> None:
        value = float(option)
        value_str = f"{value:04.1f}"
        ok = await self.coordinator.client.send_set_command(
            f"{self._cmd_prefix}{value_str}"
        )

        if ok:
            self._optimistic_override = value
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
