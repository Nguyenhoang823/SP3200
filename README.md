# SP3200
substitutions:
  bms0: "BMS"
  friendly_name: BMS
  device_name: easun_home_bms

  bms0_mac_address: C8:47:80:32:A7:F0
  bms0_protocol_version: JK02_32S

esphome:
  name: ${device_name}
  friendly_name: ${friendly_name}
  min_version: 2024.6.0

esp32:
  board: esp32-c3-devkitm-1
  framework:
    type: esp-idf

api:

ota:
  - platform: esphome
  - platform: web_server

web_server:
  port: 80

logger:
  level: DEBUG
  logs:
    esp32_ble_tracker: INFO
    esp32_ble_client: INFO

wifi:
  ssid: "Tuong Vi"
  password: "0877166823"

external_components:
  - source: github://syssi/esphome-jk-bms@main
  - source:
      type: git
      url: https://github.com/nebulous/esphome-uart-link

uart:
  id: serial_port
  tx_pin: GPIO21
  rx_pin: GPIO20
  baud_rate: 2400   # chỉnh theo baud của thiết bị RS232 của bạn

uart_tcp_server:
  id: network_port
  port: 5000
  client_mode: exclusive   # exclusive = 1 client, tốt cho command-response protocol

uart_bridge:
  uarts: [serial_port, network_port]

esp32_ble_tracker:
  scan_parameters:
    active: false

ble_client:
  - mac_address: ${bms0_mac_address}
    id: client0

jk_bms_ble:
  - ble_client_id: client0
    protocol_version: ${bms0_protocol_version}
    throttle: 1s
    id: bms0

sensor:
  - platform: wifi_signal
    name: "Tín Hiệu WiFi"
    id: signal_strength
    update_interval: 10s

  - platform: jk_bms_ble
    jk_bms_ble_id: bms0

    min_cell_voltage:
      name: "áp cell thấp nhất"
    max_cell_voltage:
      name: "áp cell cao nhất"
    min_voltage_cell:
      name: "điện áp cell thấp nhất"
    max_voltage_cell:
      name: "điện áp cell cao nhất"
    delta_cell_voltage:
      name: "điện áp lệch cell"
    average_cell_voltage:
      name: "điện áp trung bình"
    cell_voltage_1:
      name: "điện áp cell  1"
    cell_voltage_2:
      name: "điện áp cell  2"
    cell_voltage_3:
      name: "điện áp cell 3"
    cell_voltage_4:
      name: "điện áp cell 4"
    cell_voltage_5:
      name: "điện áp cell 5"
    cell_voltage_6:
      name: "điện áp cell 6"
    cell_voltage_7:
      name: "điện áp cell  7"
    cell_voltage_8:
      name: "điện áp cell  8"
    cell_resistance_1:
      name: "nội trở cell 1"
    cell_resistance_2:
      name: "nội trở cell 2"
    cell_resistance_3:
      name: "nội trở cell  3"
    cell_resistance_4:
      name: "nội trở cell  4"
    cell_resistance_5:
      name: "nội trở cell 5"
    cell_resistance_6:
      name: "nội trở cell 6"
    cell_resistance_7:
      name: "nội trở cell 7"
    cell_resistance_8:
      name: "nội trở cell 8"
    total_voltage:
      name: "điện áp khối pin"
    current:
      name: "dòng"
    power:
      name: "công suất"
    charging_power:
      name: "sạc"
    discharging_power:
      name: "xả"
    temperature_sensor_1:
      name: "nhiệt độ 1"
    temperature_sensor_2:
      name: "nhiệt độ 2"
    power_tube_temperature:
      name: "nhiệt độ bms"
    balancing:
      name: "cân bằng"
    state_of_charge:
      name: "phần trăm pin"
    capacity_remaining:
      name: "dung lượng còn lại"
    total_battery_capacity_setting:
      name: "tổng dung lượng"
    charging_cycles:
      name: "số lần sạc"
    total_charging_cycle_capacity:
      name: "tổng dung lượng xả"
    total_runtime:
      name: "thời gian hoạt động"
    balancing_current:
      name: "dòng cân bằng"

binary_sensor:
  - platform: jk_bms_ble
    jk_bms_ble_id: bms0

    balancing:
      name: "Trạng Thái Cân Bằng"

    charging:
      name: "Trạng Thái Sạc"

    discharging:
      name: "Trạng Thái Sạc Xả"

    online_status:
      name: "Trạng Thái Kết Nối BMS"

switch:
  - platform: jk_bms_ble
    jk_bms_ble_id: bms0

    charging:
      name: "Cho Phép Sạc"

    discharging:
      name: "Cho Phép Xả"

    balancer:
      name: "Cân Bằng"

time:
  - platform: homeassistant
