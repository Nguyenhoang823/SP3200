"""Number entities của Sumry Inverter."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Không tạo Number cho các điện áp pin.

    Các điện áp PBCV/PBDV/PSDV/PCVV/PBFT được tạo dưới dạng
    Select trong select.py để giao diện hiện danh sách lựa chọn.
    """
    async_add_entities([])


class InverterNumber(CoordinatorEntity, NumberEntity):
    """Giữ lớp tương thích nếu integration tham chiếu tới NumberEntity."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
