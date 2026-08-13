"""DataUpdateCoordinator: giữ 1 kết nối TCP persistent tới ESP32 bridge."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .protocol import (
    build_command, strip_and_check_crc, parse_qpigs, parse_qmod, parse_qpiws,
    parse_selectable_values, parse_qpiri, parse_qflag,
)

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 5.0
MAX_ATTEMPTS = 4           # tổng số lần thử gửi lệnh trước khi bỏ cuộc
PER_ATTEMPT_TIMEOUT = 3.0   # đợi phản hồi mỗi lần gửi
RETRY_DELAY = 1.0           # nghỉ giữa các lần gửi lại


class _BaseInverterClient:
    """
    Lớp cơ sở dùng chung cho cả 2 kiểu kết nối (TCP qua ESP32 bridge, hoặc
    Serial qua RS232-USB cắm thẳng vào máy chạy HA). Giữ 1 kết nối
    persistent xuyên suốt nhiều lần poll, thay vì mở/đóng liên tục - chỉ
    tự động kết nối lại khi có lỗi thật sự (mất kết nối, timeout không
    phản hồi).

    Dùng asyncio.Lock để đảm bảo tại 1 thời điểm chỉ có 1 lệnh được gửi/đọc
    (tránh việc coordinator đang poll mà 1 switch/select khác lại gửi lệnh
    set cùng lúc, làm lẫn lộn phản hồi).

    Lớp con chỉ cần cài đặt `_open_connection()` (trả về reader/writer kiểu
    asyncio.StreamReader/StreamWriter) và thuộc tính `_conn_desc` (chuỗi mô
    tả để log lỗi).
    """

    _conn_desc: str = "inverter"

    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def _open_connection(self):
        """Lớp con override: trả về (reader, writer)."""
        raise NotImplementedError

    async def _ensure_connected(self) -> None:
        if self._writer is not None and not self._writer.is_closing():
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                self._open_connection(), timeout=CONNECT_TIMEOUT
            )
            _LOGGER.debug("Đã kết nối (mới) tới %s", self._conn_desc)
        except (OSError, asyncio.TimeoutError, Exception) as err:  # noqa: BLE001
            self._reader = None
            self._writer = None
            raise UpdateFailed(f"Không kết nối được {self._conn_desc}: {err}") from err

    def _reset_connection(self) -> None:
        """Đóng và bỏ kết nối hiện tại, lần gọi kế tiếp sẽ tự kết nối lại."""
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:  # noqa: BLE001
                pass
        self._reader = None
        self._writer = None

    # ---- các phương thức đọc/ghi/lệnh bên dưới dùng chung, không phụ ----
    # ---- thuộc vào việc kết nối là TCP hay Serial                    ----

    async def _send_command_raw(self, cmd: str) -> bytes:
        """
        Gửi 1 lệnh, thử lại tối đa MAX_ATTEMPTS lần trên kết nối persistent.
        Tự động kết nối lại nếu socket bị đóng/lỗi giữa chừng.
        """
        async with self._lock:
            last_err = None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    await self._ensure_connected()
                    self._writer.write(build_command(cmd))
                    await self._writer.drain()
                    raw = await asyncio.wait_for(self._reader.readuntil(b"\r"), timeout=PER_ATTEMPT_TIMEOUT)
                except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, UpdateFailed) as err:
                    last_err = err
                    _LOGGER.debug(
                        "Lệnh %s lần %d/%d lỗi (%s), reset kết nối và thử lại...",
                        cmd, attempt, MAX_ATTEMPTS, err,
                    )
                    # Reset kết nối để tránh byte rác còn sót lại trong buffer
                    # làm lệch dữ liệu của lệnh kế tiếp.
                    self._reset_connection()
                    await asyncio.sleep(RETRY_DELAY)
                    continue

                body = strip_and_check_crc(raw)
                if body is None:
                    _LOGGER.debug("Lệnh %s lần %d/%d: CRC không hợp lệ, thử lại...", cmd, attempt, MAX_ATTEMPTS)
                    await asyncio.sleep(RETRY_DELAY)
                    continue

                if attempt > 1:
                    _LOGGER.info("Lệnh %s thành công sau %d lần thử", cmd, attempt)
                return body

            raise UpdateFailed(f"Không nhận được phản hồi hợp lệ cho lệnh {cmd} sau {MAX_ATTEMPTS} lần thử: {last_err}")

    async def send_set_command(self, cmd: str) -> bool:
        """
        Gửi 1 lệnh set (PE/PD/POP/PCP/PBT/PGR/PBCV/PBDV/PSDV/PCVV/PBFT/
        MNCHGC/MUCHGC...), trả về True nếu inverter phản hồi ACK.
        """
        try:
            body = await self._send_command_raw(cmd)
        except UpdateFailed as err:
            _LOGGER.warning("Không gửi được lệnh set %s: %s", cmd, err)
            return False

        text = body.decode("ascii", errors="replace")
        if "ACK" in text and "NAK" not in text:
            return True
        if "NAK" in text:
            _LOGGER.warning("Inverter từ chối lệnh %s (NAK)", cmd)
        return False

    async def query_selectable_currents(self, cmd: str) -> list[int]:
        """Gửi QMCHGCR/QMUCHGCR, trả về danh sách dòng sạc thật hỗ trợ."""
        try:
            body = await self._send_command_raw(cmd)
        except UpdateFailed as err:
            _LOGGER.warning("Không lấy được danh sách dòng sạc (%s): %s", cmd, err)
            return []
        return parse_selectable_values(body)

    async def fetch_all(self) -> dict:
        """Gửi lần lượt các lệnh đọc trên kết nối persistent, gộp kết quả."""
        data: dict = {}

        qpigs = await self._send_command_raw("QPIGS")
        data.update(parse_qpigs(qpigs))

        qmod = await self._send_command_raw("QMOD")
        data.update(parse_qmod(qmod))

        qpiws = await self._send_command_raw("QPIWS")
        data.update(parse_qpiws(qpiws))

        # QPIRI/QFLAG: không bắt buộc, lỗi ở đây không làm hỏng sensor chính
        try:
            qpiri = await self._send_command_raw("QPIRI")
            data.update(parse_qpiri(qpiri))
        except UpdateFailed as err:
            _LOGGER.debug("Không lấy được QPIRI (không ảnh hưởng sensor chính): %s", err)

        try:
            qflag = await self._send_command_raw("QFLAG")
            data.update(parse_qflag(qflag))
        except UpdateFailed as err:
            _LOGGER.debug("Không lấy được QFLAG (không ảnh hưởng sensor chính): %s", err)

        return data

    async def async_close(self) -> None:
        """Đóng kết nối hẳn - gọi khi unload integration."""
        async with self._lock:
            self._reset_connection()


class InverterTcpClient(_BaseInverterClient):
    """Kết nối qua ESP32 TCP-UART bridge (stream_server/uart_tcp_server)."""

    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self._conn_desc = f"ESP32 bridge {host}:{port}"

    async def _open_connection(self):
        return await asyncio.open_connection(self.host, self.port)


class InverterSerialClient(_BaseInverterClient):
    """
    Kết nối trực tiếp qua cổng RS232-USB cắm vào máy chạy Home Assistant
    (ví dụ /dev/ttyUSB0), không qua ESP32 bridge.

    Yêu cầu package `pyserial-asyncio` (khai trong manifest.json) vì
    open_serial_connection() trả về asyncio.StreamReader/StreamWriter
    giống hệt asyncio.open_connection(), nên toàn bộ logic gửi/nhận/retry
    ở lớp cha dùng lại được nguyên vẹn, không cần viết riêng.
    """

    def __init__(
        self,
        serial_port: str,
        baud_rate: int = 2400,
        data_bits: int = 8,
        parity: str = "N",
        stop_bits: float = 1,
    ):
        super().__init__()
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self._conn_desc = (
            f"cổng serial {serial_port}@{baud_rate} {data_bits}{parity}{stop_bits}"
        )

    async def _open_connection(self):
        import serial_asyncio  # import trễ để không bắt buộc cài khi chỉ dùng TCP

        return await serial_asyncio.open_serial_connection(
            url=self.serial_port,
            baudrate=self.baud_rate,
            bytesize=self.data_bits,
            parity=self.parity,
            stopbits=self.stop_bits,
        )


class InverterDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: _BaseInverterClient, scan_interval: int):
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name="Sumry Inverter",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict:
        return await self.client.fetch_all()
