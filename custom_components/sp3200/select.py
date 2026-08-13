"""Select entities: các lựa chọn dạng enum (POP/PCP/PBT/PGR)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# Mỗi định nghĩa: (tên hiển thị, prefix lệnh set, {label: mã 2 số})
SELECT_DEFS = {
    "output_source_priority": (
        "Chế Độ Tải",
        "POP",
        {"SUB": "00", "SBU": "02"},
    ),
    "charger_source_priority": (
        "Chế Độ Sạc",
        "PCP",
        {"CSO": "01", "SNU": "02", "OSO": "03"},
    ),
    
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InverterSelect(coordinator, entry, key, name, prefix, options)
        for key, (name, prefix, options) in SELECT_DEFS.items()
    ]

    # Dòng sạc chính: dùng MNCHGC (3 chữ số, hỗ trợ >100A) - ĐÃ XÁC NHẬN
    # bằng test thực tế rằng lệnh cũ MCHGC (2 chữ số) bị NAK ở giá trị cao
    # (60/70/80A), trong khi MNCHGC0080 và MNCHGC0110 đều ACK thành công.
    mchgc_options = getattr(coordinator, "mchgc_options", [])
    if mchgc_options:
        entities.append(
            InverterCurrentSelect(
                coordinator, entry, "max_charging_current", "Dòng Sạc PV",
                "MNCHGC0", mchgc_options, digits=3,
            )
        )

    # Dòng sạc từ lưới (utility): CHƯA test riêng lệnh MUCHGC ở giá trị cao,
    # giữ nguyên định dạng 2 chữ số cũ - báo lại nếu bị NAK ở mức >40A để tôi
    # kiểm tra xem có tồn tại lệnh "MNUCHGC" tương tự MNCHGC hay không.
    muchgc_options = getattr(coordinator, "muchgc_options", [])
    if muchgc_options:
        entities.append(
            InverterCurrentSelect(
                coordinator, entry, "max_utility_charging_current", "Dòng Sạc Lưới",
                "MUCHGC0", muchgc_options, digits=2,
            )
        )

    entities.append(InverterVoltageSelect(coordinator, entry))

    async_add_entities(entities)


class InverterCurrentSelect(CoordinatorEntity, SelectEntity):
    """
    Select dòng sạc tối đa, options lấy TRỰC TIẾP từ QMCHGCR/QMUCHGCR lúc
    khởi động - đảm bảo chỉ cho chọn giá trị inverter thực sự báo hỗ trợ.
    `digits` quyết định độ rộng số khi format lệnh set (2 cho MUCHGC cũ,
    3 cho MNCHGC mới - vì MNCHGC hỗ trợ >100A nên cần 3 chữ số).
    """

    def __init__(self, coordinator, entry, key: str, name: str, cmd_prefix: str, values: list[int], digits: int = 2):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._cmd_prefix = cmd_prefix
        self._digits = digits
        self._value_map = {f"{v}A": v for v in values}
        self._amps_to_label = {v: f"{v}A" for v in values}
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_unique_id = f"{entry.entry_id}_select_{key}"
        self._attr_options = list(self._value_map.keys())
        self._optimistic_override: str | None = None

    @property
    def current_option(self):
        # QPIRI trả current_max_charging_current (dòng sạc chính đang đặt)
        if self._key == "max_charging_current":
            amps = self.coordinator.data.get("current_max_charging_current")
        elif self._key == "max_utility_charging_current":
            amps = self.coordinator.data.get("current_max_ac_charging_current")
        else:
            amps = None

        if amps is not None and amps in self._amps_to_label:
            self._optimistic_override = None
            return self._amps_to_label[amps]
        return self._optimistic_override

    async def async_select_option(self, option: str) -> None:
        amps = self._value_map.get(option)
        if amps is None:
            return
        value_str = f"{amps:0{self._digits}d}"
        ok = await self.coordinator.client.send_set_command(f"{self._cmd_prefix}{value_str}")
        if ok:
            self._optimistic_override = option
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})


class InverterVoltageSelect(CoordinatorEntity, SelectEntity):
    """
    Select điện áp định mức đầu ra (lệnh V<nnn>, đọc lại từ QPIRI field
    "AC output rating voltage" - output_rating_voltage). Chỉ áp dụng cho
    model HV: 220V/230V/240V. Model LV dùng 110/120/127V - CHƯA hỗ trợ,
    báo lại nếu bạn dùng model LV để tôi thêm option tương ứng.

    Lưu ý: đây là điện áp ĐỊNH MỨC (rating) của inverter, không phải điện
    áp lưới đang đo (đó là QPIGS). Một số model yêu cầu tắt/bật lại
    inverter hoặc ngắt tải để lệnh có hiệu lực - nếu bị NAK liên tục dù
    đúng cú pháp, khả năng cao model không hỗ trợ đổi qua phần mềm.
    """

    _VALUES = [220, 230, 240]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Điện Áp Tải "
        self._attr_unique_id = f"{entry.entry_id}_select_output_rating_voltage"
        self._attr_options = [f"{v}V" for v in self._VALUES]
        self._optimistic_override: str | None = None

    @property
    def current_option(self):
        voltage = self.coordinator.data.get("output_rating_voltage")
        if voltage is not None:
            # QPIRI trả về vd "230.0" - so khớp với giá trị gần nhất trong
            # dung sai nhỏ để tránh lệch do làm tròn thập phân.
            nearest = min(self._VALUES, key=lambda v: abs(v - voltage))
            if abs(nearest - voltage) <= 2:
                self._optimistic_override = None
                return f"{nearest}V"
        return self._optimistic_override

    async def async_select_option(self, option: str) -> None:
        try:
            value = int(option.rstrip("V"))
        except ValueError:
            return
        if value not in self._VALUES:
            return
        ok = await self.coordinator.client.send_set_command(f"V{value:03d}")
        if ok:
            self._optimistic_override = option
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})


# key trong coordinator.data (từ QPIRI) tương ứng với mỗi select
SELECT_DATA_KEY = {
    "output_source_priority": "output_source_priority_code",
    "charger_source_priority": "charger_source_priority_code",
    "battery_type": "battery_type_code",
    "grid_working_range": "grid_working_range_code",
}


class InverterSelect(CoordinatorEntity, SelectEntity):
    """
    Select đọc trạng thái thật từ QPIRI (qua coordinator.data) mỗi lần poll.
    Nếu vừa gửi lệnh set thành công, hiển thị ngay giá trị mới trong lúc chờ
    lần poll kế tiếp xác nhận lại (fallback về optimistic tạm thời).
    """

    def __init__(self, coordinator, entry, key: str, name: str, cmd_prefix: str, options: dict[str, str]):
        super().__init__(coordinator)
        self._key = key
        self._entry = entry
        self._cmd_prefix = cmd_prefix
        self._options = options  # label -> mã số
        self._code_to_label = {v: k for k, v in options.items()}
        self._data_key = SELECT_DATA_KEY.get(key)
        self._attr_name = f"Sumry Inverter {name}"
        self._attr_unique_id = f"{entry.entry_id}_select_{key}"
        self._attr_options = list(options.keys())
        self._optimistic_override: str | None = None

    @property
    def current_option(self):
        # Ưu tiên giá trị thật đọc từ QPIRI; nếu chưa có (QPIRI lỗi/model
        # không hỗ trợ) thì tạm dùng giá trị optimistic vừa set gần nhất.
        if self._data_key:
            code = self.coordinator.data.get(self._data_key)
            if code is not None:
                # code có thể là "0"/"00" tùy field - thử khớp cả 2 kiểu
                label = self._code_to_label.get(code) or self._code_to_label.get(code.zfill(2))
                if label:
                    self._optimistic_override = None
                    return label
        return self._optimistic_override

    async def async_select_option(self, option: str) -> None:
        code = self._options.get(option)
        if code is None:
            return
        ok = await self.coordinator.client.send_set_command(f"{self._cmd_prefix}{code}")
        if ok:
            self._optimistic_override = option
            self.async_write_ha_state()
            # Xin cập nhật lại ngay để đồng bộ QPIRI sớm thay vì chờ scan_interval
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)})

