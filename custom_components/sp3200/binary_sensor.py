"""Binary sensors: load on/off, charging on/off, cảnh báo chung."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

BINARY_DEFS = {
    "load_on": ("Trạng Thái Tải", BinarySensorDeviceClass.POWER),
    "charging_on": ("Trạng Thái Sạc", BinarySensorDeviceClass.BATTERY_CHARGING),
    "ac_charging_on": ("Sạc Từ Lưới", BinarySensorDeviceClass.BATTERY_CHARGING),
    "scc_charging_on": ("Sạc Từ PV", BinarySensorDeviceClass.BATTERY_CHARGING),
    "any_warning": ("Warning Active", BinarySensorDeviceClass.PROBLEM),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InverterBinarySensor(coordinator, entry, key, name, dclass)
        for key, (name, dclass) in BINARY_DEFS.items()
    ]
    async_add_entities(entities)


class InverterBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, device_class):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_device_class = device_class
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self._key))

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
