"""Constants cho HS/MS/MSX inverter integration."""

DOMAIN = "sp3200"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUD_RATE = "baud_rate"
CONF_DATA_BITS = "data_bits"
CONF_PARITY = "parity"
CONF_STOP_BITS = "stop_bits"

CONNECTION_TCP = "tcp"
CONNECTION_SERIAL = "serial"

DEFAULT_PORT = 8899
DEFAULT_SCAN_INTERVAL = 10  # giây
DEFAULT_BAUD_RATE = 2400   # theo tài liệu HS/MS/MSX: 2400 8N1
DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_DATA_BITS = 8
DEFAULT_PARITY = "N"
DEFAULT_STOP_BITS = 1

# Các baud rate chuẩn quốc tế (theo thông lệ EIA/TIA-232), dùng cho dropdown
# chọn trong config_flow - tránh người dùng gõ tay sai giá trị.
STANDARD_BAUD_RATES = [
    1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200,
]

# pyserial dùng ký tự 1 chữ cái cho parity: N=None, E=Even, O=Odd, M=Mark, S=Space
PARITY_OPTIONS = {
    "N": "None (không kiểm tra)",
    "E": "Even (chẵn)",
    "O": "Odd (lẻ)",
    "M": "Mark",
    "S": "Space",
}

DATA_BITS_OPTIONS = [5, 6, 7, 8]

# pyserial nhận stopbits dạng số (1, 1.5, 2); dùng chuỗi làm key cho vol.In
# vì 1.5 (float) làm key khó chọn chính xác trên UI, ta map lại khi tạo client.
STOP_BITS_OPTIONS = {
    "1": "1",
    "1.5": "1.5",
    "2": "2",
}

# Mã chế độ QMOD -> nghĩa
DEVICE_MODES = {
    "P": "Power On",
    "S": "Standby",
    "L": "Line (Grid)",
    "B": "Battery",
    "F": "Fault",
    "H": "Power Saving",
}
