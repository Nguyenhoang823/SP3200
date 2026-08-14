"""Switch entities: các cờ enable/disable qua lệnh PE<x>/PD<x> (mục 2.6 / 3.1)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# key cờ (theo tài liệu QFLAG/PE/PD) -> tên hiển thị
FLAG_DEFS = {
    "a": "Âm Bíp",
    "b": "Bypass Khi Quá Tải",
    "j": "Tiết Kiệm Điện",
    "k": "Quay Về Màn Hình Chính",
    "u": "Khởi Động Lại Khi Quá Tải",
    "v": "Khởi Động Lại Khi Quá Nhiệt",
    "x": "Đèn Nền",
    "y": "Âm Báo Khi Mất Lưới",
    "z": "Ghi Lại Lỗi",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InverterFlagSwitch(coordinator, entry, flag, name) for flag, name in FLAG_DEFS.items()
    ]
    async_add_entities(entities)


class InverterFlagSwitch(CoordinatorEntity, SwitchEntity):
    """Switch đọc trạng thái thật từ QFLAG (qua coordinator.data) mỗi lần poll."""

    def __init__(self, coordinator, entry, flag: str, name: str):
        super().__init__(coordinator)
        self._flag = flag
        self._entry = entry
        self._data_key = f"flag_{flag}"
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_unique_id = f"{entry.entry_id}_flag_{flag}"
        self._optimistic_override: bool | None = None

    @property
    def is_on(self):
        value = self.coordinator.data.get(self._data_key)
        if value is not None:
            self._optimistic_override = None
            return value
        return self._optimistic_override

    async def async_turn_on(self, **kwargs):
        ok = await self.coordinator.client.send_set_command(f"PE{self._flag}")
        if ok:
            self._optimistic_override = True
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        ok = await self.coordinator.client.send_set_command(f"PD{self._flag}")
        if ok:
            self._optimistic_override = False
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
