"""Sensor entities cho Sumry Inverter."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_MODES

# key data -> (tên hiển thị, đơn vị, device_class, state_class)
SENSOR_DEFS = {
    "grid_voltage": ("Điện áp lưới", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "grid_frequency": ("Tần số lưới", "Hz", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT),
    "ac_output_voltage": ("Điện áp đầu ra AC", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "ac_output_frequency": ("Tần số đầu ra AC", "Hz", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT),
    "ac_output_apparent_power": ("Công suất biểu kiến AC", "VA", SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    "ac_output_active_power": ("Công suất thực AC", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "output_load_percent": ("Tải đầu ra", "%", None, SensorStateClass.MEASUREMENT),
    "bus_voltage": ("Điện áp Bus", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "battery_voltage": ("Điện áp pin", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "battery_charging_current": ("Dòng sạc pin", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "battery_capacity": ("Dung lượng pin", "%", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT),
    "inverter_heatsink_temp": ("Nhiệt độ tản nhiệt inverter", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "pv_input_current": ("Dòng vào PV", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "pv_input_voltage": ("Điện áp vào PV", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "battery_voltage_scc": ("Điện áp pin (SCC)", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "battery_discharge_current": ("Dòng xả pin", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "pv_charging_power": ("Công suất sạc PV", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "pv_power_calculated": ("Công suất PV (V×I)", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "battery_charging_power": ("Công suất sạc pin", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "battery_discharging_power": ("Công suất xả pin", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        InverterSensor(coordinator, entry, key, *meta) for key, meta in SENSOR_DEFS.items()
    ]
    entities.append(InverterModeSensor(coordinator, entry))
    async_add_entities(entities)


class InverterSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, unit, device_class, state_class):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Sumry Inverter",
            manufacturer="Sumry",
            model="HS/MS/MSX",
        )


class InverterModeSensor(CoordinatorEntity, SensorEntity):
    """Sensor riêng cho chế độ hoạt động (QMOD), map code -> tên dễ đọc."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Chế Độ Sử Dụng"
        self._attr_unique_id = f"{entry.entry_id}_mode"

    @property
    def native_value(self):
        code = self.coordinator.data.get("mode_code")
        return DEVICE_MODES.get(code, code)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})
