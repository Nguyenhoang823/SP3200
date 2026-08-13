"""HS/MS/MSX Inverter integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL,
    CONF_CONNECTION_TYPE, CONF_SERIAL_PORT, CONF_BAUD_RATE,
    CONF_DATA_BITS, CONF_PARITY, CONF_STOP_BITS,
    CONNECTION_TCP, CONNECTION_SERIAL, DEFAULT_BAUD_RATE,
    DEFAULT_DATA_BITS, DEFAULT_PARITY, DEFAULT_STOP_BITS,
)
from .coordinator import InverterDataUpdateCoordinator, InverterTcpClient, InverterSerialClient

PLATFORMS = ["sensor", "binary_sensor", "switch", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # entry cũ (tạo trước khi có tuỳ chọn serial) không có CONF_CONNECTION_TYPE
    # -> mặc định coi là TCP để không phá cấu hình đang chạy của người dùng.
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP)

    if connection_type == CONNECTION_SERIAL:
        # Ưu tiên giá trị đã chỉnh trong Options (Cấu hình > tuỳ chọn tích
        # hợp), fallback về giá trị lúc setup ban đầu nếu chưa từng chỉnh.
        cfg = {**entry.data, **entry.options}
        client = InverterSerialClient(
            cfg[CONF_SERIAL_PORT],
            cfg.get(CONF_BAUD_RATE, DEFAULT_BAUD_RATE),
            cfg.get(CONF_DATA_BITS, DEFAULT_DATA_BITS),
            cfg.get(CONF_PARITY, DEFAULT_PARITY),
            cfg.get(CONF_STOP_BITS, DEFAULT_STOP_BITS),
        )
    else:
        client = InverterTcpClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    coordinator = InverterDataUpdateCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    # Hỏi thẳng inverter xem nó thực sự hỗ trợ dòng sạc tối đa bao nhiêu A
    # (không dùng số mặc định 50A trong tài liệu, mỗi model có thể khác nhau)
    coordinator.mchgc_options = await coordinator.client.query_selectable_currents("QMCHGCR")
    coordinator.muchgc_options = await coordinator.client.query_selectable_currents("QMUCHGCR")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Khi người dùng lưu Options (vd. đổi baud_rate, serial_port,
    # scan_interval) -> tự reload để tạo lại client với giá trị mới, không
    # cần khởi động lại HA.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: InverterDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.async_close()
    return unload_ok
