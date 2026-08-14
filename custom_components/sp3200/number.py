"""Number entities: các ngưỡng điện áp ắc-quy dạng nn.n (PBCV/PBDV/PSDV/PCVV/PBFT)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# key -> (tên hiển thị, prefix lệnh, min, max, step)
# Khoảng min/max lấy tương đối theo tài liệu (đơn vị 48V), điều chỉnh nếu
# inverter của bạn là 12V/24V.
NUMBER_DEFS = {
    "battery_recharge_voltage": ("Điện Áp Chuyển Nguồn", "PBCV", 22.0, 25.5, 0.5),
    "battery_redischarge_voltage": ("Điện Áp Xả Tải", "PBDV", 25.0, 28.0, 0.5),
    "battery_cutoff_voltage": ("Điện Áp Tắt Máy", "PSDV", 22.0, 24.0, 0.1),
    "battery_cv_voltage": ("Điện Áp Đầy Pin", "PCVV", 27.0, 29.0, 0.1),
    "battery_float_voltage": ("Điện Áp Sạc Thả Nổi", "PBFT", 27.5, 28.5, 0.1),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InverterVoltageNumber(coordinator, entry, key, name, prefix, vmin, vmax, step)
        for key, (name, prefix, vmin, vmax, step) in NUMBER_DEFS.items()
    ]
    async_add_entities(entities)


# key trong coordinator.data (từ QPIRI) tương ứng với mỗi number
NUMBER_DATA_KEY = {
    "battery_recharge_voltage": "battery_recharge_voltage",
    "battery_redischarge_voltage": "battery_redischarge_voltage",
    "battery_cutoff_voltage": "battery_under_voltage",
    "battery_cv_voltage": "battery_cv_voltage",
    "battery_float_voltage": "battery_float_voltage",
}


class InverterVoltageNumber(CoordinatorEntity, NumberEntity):
    """Number đọc giá trị thật từ QPIRI (qua coordinator.data) mỗi lần poll."""

    def __init__(self, coordinator, entry, key: str, name: str, cmd_prefix: str, vmin: float, vmax: float, step: float):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._cmd_prefix = cmd_prefix
        self._data_key = NUMBER_DATA_KEY.get(key)
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_unique_id = f"{entry.entry_id}_number_{key}"
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = "V"
        self._attr_mode = NumberMode.BOX
        self._optimistic_override: float | None = None

    @property
    def native_value(self):
        if self._data_key:
            value = self.coordinator.data.get(self._data_key)
            if value is not None:
                self._optimistic_override = None
                return value
        return self._optimistic_override

    async def async_set_native_value(self, value: float) -> None:
        value_str = f"{value:04.1f}"  # ví dụ 48.0, 51.5
        ok = await self.coordinator.client.send_set_command(f"{self._cmd_prefix}{value_str}")
        if ok:
            self._optimistic_override = value
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
