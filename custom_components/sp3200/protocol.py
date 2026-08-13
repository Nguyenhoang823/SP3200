"""
Giao thức RS232 (HS/MS/MSX series) - CRC-16/XMODEM + parser.

Đã xác nhận bằng dữ liệu thực tế: firmware inverter dùng CRC-16/XMODEM THUẦN
(polynomial 0x1021, không có bước hoán đổi byte / điều chỉnh offset như thuật
toán Voltronic "chuẩn" tài liệu mô tả). Lệnh gửi xuống cũng được inverter chấp
nhận ngay cả khi KHÔNG có CRC (chỉ cần kết thúc bằng \\r\\n), nhưng để an toàn
với các lệnh set (P-command) vẫn luôn tính CRC-XMODEM đúng khi gửi.
"""
from __future__ import annotations


def calc_crc(data: bytes) -> bytes:
    """CRC-16/XMODEM chuẩn (poly 0x1021, init 0), trả về 2 byte MSB-first."""
    crc = 0
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021)
            else:
                crc <<= 1
            crc &= 0xFFFF
    return bytes([crc >> 8, crc & 0xFF])


def build_command(cmd: str) -> bytes:
    """Ghép lệnh ASCII + CRC-XMODEM + <cr>. Ví dụ: build_command('QPIGS')."""
    payload = cmd.encode("ascii")
    crc = calc_crc(payload)
    return payload + crc + b"\r"


def strip_and_check_crc(raw: bytes) -> bytes | None:
    """
    Kiểm tra CRC của phản hồi và trả về phần data thô (không CRC, không <cr>).
    Trả về None nếu CRC sai hoặc frame không hợp lệ.
    """
    if len(raw) < 4 or not raw.endswith(b"\r"):
        return None
    body = raw[:-3]        # bỏ 2 byte CRC + \r
    recv_crc = raw[-3:-1]
    calc = calc_crc(body)
    if calc != recv_crc:
        return None
    return body


def parse_qpigs(body: bytes) -> dict:
    """
    Parse phản hồi QPIGS - ĐÃ CHỈNH KHỚP DỮ LIỆU THỰC TẾ từ inverter:
    (BBB.B CC.C DDD.D EE.E FFFF GGGG HHH III JJ.JJ KKK OOO TTTT EEEE
      UUU.U WW.WW PPPPP b7b6b5b4b3b2b1b0 QQ VV MMMMM b10b9b8
    Lưu ý: KKK ở đây là 3 chữ số (khác bản PDF gốc ghi KK 2 chữ số), và có
    thêm 4 field mở rộng (QQ, VV, MMMMM, b10b9b8) không có trong tài liệu gốc
    - có thể là thông tin PV2/mở rộng riêng của model này, ý nghĩa chưa xác nhận.
    """
    text = body.decode("ascii", errors="replace").lstrip("(")
    parts = text.split()
    if len(parts) < 17:
        return {}

    (
        grid_voltage, grid_freq, ac_out_voltage, ac_out_freq,
        ac_out_apparent_power, ac_out_active_power, load_percent,
        bus_voltage, battery_voltage, battery_charge_current,
        battery_capacity, heatsink_temp, pv_input_current,
        pv_input_voltage, battery_voltage_scc, battery_discharge_current,
        status_bits,
    ) = parts[:17]

    result = {
        "grid_voltage": float(grid_voltage),
        "grid_frequency": float(grid_freq),
        "ac_output_voltage": float(ac_out_voltage),
        "ac_output_frequency": float(ac_out_freq),
        "ac_output_apparent_power": int(ac_out_apparent_power),
        "ac_output_active_power": int(ac_out_active_power),
        "output_load_percent": int(load_percent),
        "bus_voltage": int(bus_voltage),
        "battery_voltage": float(battery_voltage),
        "battery_charging_current": int(battery_charge_current),
        "battery_capacity": int(battery_capacity),
        "inverter_heatsink_temp": int(heatsink_temp),
        "pv_input_current": int(pv_input_current),
        "pv_input_voltage": float(pv_input_voltage),
        "battery_voltage_scc": float(battery_voltage_scc),
        "battery_discharge_current": int(battery_discharge_current),
    }

    if len(status_bits) == 8:
        result["load_on"] = status_bits[4] == "1"
        result["charging_on"] = status_bits[5] == "1"
        result["scc_charging_on"] = status_bits[6] == "1"
        result["ac_charging_on"] = status_bits[7] == "1"

    # Công suất sạc/xả ắc-quy (tính từ V*I, không có field trực tiếp trong QPIGS)
    result["battery_charging_power"] = round(result["battery_voltage"] * result["battery_charging_current"], 1)
    result["battery_discharging_power"] = round(result["battery_voltage"] * result["battery_discharge_current"], 1)

    # Công suất PV tính từ V*I - dùng làm công thức dự phòng/đối chiếu với
    # field MMMMM bên dưới (chưa chắc field nào đúng, cần dữ liệu thật lúc
    # có nắng để so sánh)
    result["pv_power_calculated"] = round(result["pv_input_voltage"] * result["pv_input_current"], 1)

    # Field mở rộng: dựa theo dữ liệu thực tế thu được, field thứ 20 (MMMMM,
    # 5 chữ số) là công suất sạc PV (W). Field QQ/VV/b10b9b8 chưa xác định
    # rõ ý nghĩa, vẫn lưu thô để tham khảo.
    extra_fields = parts[17:]
    if len(extra_fields) >= 3:
        try:
            result["pv_charging_power"] = int(extra_fields[2])  # MMMMM
        except (ValueError, IndexError):
            pass
    if extra_fields:
        result["extra_raw_fields"] = " ".join(extra_fields)

    return result


def parse_qmod(body: bytes) -> dict:
    """Parse phản hồi QMOD: (M -> trả về ký tự mode."""
    text = body.decode("ascii", errors="replace").lstrip("(").strip()
    return {"mode_code": text}


def parse_qpiws(body: bytes) -> dict:
    """Parse phản hồi QPIWS: (a0a1...a31 -> trả về danh sách cảnh báo đang bật."""
    text = body.decode("ascii", errors="replace").lstrip("(").strip()
    bits = [c for c in text if c in "01"]
    warnings = {f"warn_bit_{i}": (b == "1") for i, b in enumerate(bits)}
    warnings["any_warning"] = any(b == "1" for b in bits)
    return warnings


def parse_selectable_values(body: bytes) -> list[int]:
    """
    Parse phản hồi QMCHGCR / QMUCHGCR: (AAA BBB CCC DDD...
    Trả về danh sách các giá trị dòng sạc (A) mà inverter THỰC SỰ hỗ trợ -
    đây mới là giới hạn thật, không phải giới hạn do code áp đặt.
    """
    text = body.decode("ascii", errors="replace").lstrip("(").strip()
    values = []
    for token in text.split():
        try:
            values.append(int(token))
        except ValueError:
            continue
    return values


def parse_qpiri(body: bytes) -> dict:
    """
    Parse phản hồi QPIRI (Device Rating Information) - lấy các giá trị
    CÀI ĐẶT HIỆN TẠI thật (không phải giá trị đo real-time như QPIGS).
    Format theo tài liệu:
    (BBB.B CC.C DDD.D EE.E FF.F HHHH IIII JJ.J KK.K JJ.J KK.K LL.L O PP Q0
      O P Q R SS T U VV.V W X
    Lưu ý: có thể lệch vị trí/số field thực tế so với tài liệu (giống QPIGS
    trước đây) - nếu parse ra sai, gửi lại response thật để tôi chỉnh.
    """
    text = body.decode("ascii", errors="replace").lstrip("(").strip()
    parts = text.split()
    if len(parts) < 25:
        return {}

    result = {}
    try:
        result["output_rating_voltage"] = float(parts[2])    # DDD.D: AC output rating voltage (220/230/240)
        result["battery_type_code"] = parts[12]              # O: 0 AGM,1 Flooded,2 User
        result["current_max_ac_charging_current"] = int(parts[13])   # PP
        result["current_max_charging_current"] = int(parts[14])      # Q0
        result["grid_working_range_code"] = parts[15]         # O(2): 0 appliance,1 UPS
        result["output_source_priority_code"] = parts[16]     # P(2): 0/1/2
        result["charger_source_priority_code"] = parts[17]    # Q(2): 0/1/2/3
        result["battery_recharge_voltage"] = float(parts[8])   # KK.K
        result["battery_under_voltage"] = float(parts[9])       # JJ.J (2nd)
        result["battery_cv_voltage"] = float(parts[10])          # KK.K (bulk)
        result["battery_float_voltage"] = float(parts[11])       # LL.L
        result["battery_redischarge_voltage"] = float(parts[22]) # VV.V
    except (ValueError, IndexError):
        pass

    return result


# Các ký tự cờ hợp lệ theo QFLAG (mục 2.6) - dùng chung với switch.py
FLAG_LETTERS = ["a", "b", "j", "k", "u", "v", "x", "y", "z"]


def parse_qflag(body: bytes) -> dict:
    """
    Parse phản hồi QFLAG: (ExxxDxxx - E=các cờ đang enable, D=các cờ đang
    disable, nối liền nhau không có khoảng trắng. Trả về dict {chữ_cờ: bool}.
    """
    text = body.decode("ascii", errors="replace").lstrip("(").strip()

    enabled_part = ""
    disabled_part = ""
    if text.startswith("E"):
        rest = text[1:]
        if "D" in rest:
            enabled_part, _, disabled_part = rest.partition("D")
        else:
            enabled_part = rest
    elif text.startswith("D"):
        disabled_part = text[1:]

    result = {}
    for letter in FLAG_LETTERS:
        if letter in enabled_part:
            result[f"flag_{letter}"] = True
        elif letter in disabled_part:
            result[f"flag_{letter}"] = False

    return result

