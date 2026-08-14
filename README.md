Sumry Inverter (HS/MS/MSX) - Home Assistant Custom Integration
Custom integration cho Home Assistant, đọc dữ liệu và điều khiển biến tần dòng HS/MS/MSX hãng Sumry và tương đương) qua RS232.

Hỗ trợ 2 kiểu kết nối:

ESP32 TCP bridge - dùng ESPHome mở cổng TCP-UART (WiFi), dùng khi biến tần đặt xa máy chạy Home Assistant.
RS232-USB trực tiếp - cắm thẳng cáp RS232-to-USB vào máy chạy Home Assistant, không cần thêm phần cứng ESP32. Cấu hình được đầy đủ baud rate, data bits, parity, stop bits theo chuẩn quốc tế.
Tính năng
Đọc đầy đủ thông số : điện áp lưới/tải/battery, tần số, công suất, % tải, nhiệt độ, dòng/điện áp PV...
Switch điều khiển các cờ cấu hình (buzzer, bypass, power saving, backlight, cảnh báo mất lưới, ghi lỗi...), tự đồng bộ trạng thái thật từ biến tần.
Select chọn chế độ nguồn tải, nguồn sạc, dòng sạc tối đa (tự dò danh sách dòng sạc thật hỗ trợ qua).
Number/select khác cho các thông số cấu hình còn lại.
Cài đặt
Qua HACS (khuyến nghị)
HACS -> Integrations -> menu 3 chấm -> Custom repositories.
Thêm URL repo này, chọn loại Integration.
Tìm "Sumry Inverter" trong HACS, bấm Download.
Restart Home Assistant.
Thủ công
Copy thư mục custom_components/hs_ms_msx_inverter vào thư mục config/custom_components/ của Home Assistant, sau đó restart.

Cấu hình
Settings -> Devices & Services -> Add Integration -> tìm "Sumry Inverter", chọn kiểu kết nối (TCP hoặc Serial) và điền thông số tương ứng.

License
MIT
