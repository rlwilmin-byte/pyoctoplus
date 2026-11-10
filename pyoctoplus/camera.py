"""
Core driver implementation for Teledyne e2v OctoPlus USB 3.0 line scan cameras.
Uses libusb-1.0 via ctypes for cross-platform, zero-dependency USB communication.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
import struct
import sys
import time
from typing import Optional, Tuple, Dict, Any

from pyoctoplus.registers import (
    VENDOR_ID_E2V,
    PRODUCT_IDS_OCTOPLUS,
    EP_STREAM_IN,
    BM_REQ_VENDOR_IN,
    BM_REQ_VENDOR_OUT,
    REQ_GET_STATUS,
    REQ_WRITE_REG,
    REQ_READ_REG,
    U3V_LEADER_MAGIC,
    REG_MANUFACTURER_NAME,
    REG_MODEL_NAME,
    REG_SERIAL_NUMBER,
    REG_FIRMWARE_VERSION,
    REG_STATUS,
    REG_ACQUISITION_START,
    REG_ACQUISITION_STOP,
    REG_FLUSH_BUFFER,
    REG_SENSOR_WIDTH,
    REG_ROI_WIDTH,
    REG_PIXEL_FORMAT,
    REG_REVERSE_READING,
    REG_TEST_PATTERN,
    REG_TEST_IMAGE_HEIGHT,
    REG_LINE_PERIOD,
    REG_LINE_PERIOD_MIN,
    REG_EXPOSURE_TIME,
    REG_EXPOSURE_TIME_MIN,
    REG_EXPOSURE_TIME_MAX,
    REG_TRIGGER_MODE,
    REG_ANALOG_GAIN,
    REG_DIGITAL_GAIN,
    REG_DIGITAL_OFFSET,
    REG_GPO_CONFIG,
    TriggerMode,
    PixelFormat,
    AnalogGain,
    TestPattern,
    GpoMode,
    CameraStatusFlags,
)

# ---------------------------------------------------------------------------
# libusb-1.0 ctypes wrapper
# ---------------------------------------------------------------------------

def _load_libusb():
    system = platform.system()
    lib_names = []
    if system == "Linux":
        lib_names = ["libusb-1.0.so.0", "libusb-1.0.so"]
    elif system == "Darwin":
        lib_names = [
            "libusb-1.0.dylib",
            "/opt/homebrew/lib/libusb-1.0.dylib",
            "/usr/local/lib/libusb-1.0.dylib",
        ]
    elif system == "Windows":
        lib_names = ["libusb-1.0.dll", "usb-1.0.dll"]

    # Try ctypes.util.find_library
    found = ctypes.util.find_library("usb-1.0") or ctypes.util.find_library("libusb-1.0")
    if found:
        lib_names.insert(0, found)

    for name in lib_names:
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue

    raise RuntimeError(
        f"Could not load libusb-1.0 on {system}. Please ensure libusb-1.0 is installed."
    )


class _DeviceDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", ctypes.c_uint8),
        ("bDescriptorType", ctypes.c_uint8),
        ("bcdUSB", ctypes.c_uint16),
        ("bDeviceClass", ctypes.c_uint8),
        ("bDeviceSubClass", ctypes.c_uint8),
        ("bDeviceProtocol", ctypes.c_uint8),
        ("bMaxPacketSize0", ctypes.c_uint8),
        ("idVendor", ctypes.c_uint16),
        ("idProduct", ctypes.c_uint16),
        ("bcdDevice", ctypes.c_uint16),
        ("iManufacturer", ctypes.c_uint8),
        ("iProduct", ctypes.c_uint8),
        ("iSerialNumber", ctypes.c_uint8),
        ("bNumConfigurations", ctypes.c_uint8),
    ]


class OctoPlusError(Exception):
    """Base exception for OctoPlus camera operations."""
    pass


class OctoPlusCamera:
    """
    High-level cross-platform controller for Teledyne e2v OctoPlus USB 3.0 line cameras.
    """

    def __init__(self, vid: int = VENDOR_ID_E2V, pid: Optional[int] = None):
        self.vid = vid
        self.pid = pid
        self._lib = _load_libusb()
        self._setup_libusb_signatures()
        self._ctx = ctypes.c_void_p(0)
        self._handle = None
        self._is_open = False
        self._sensor_width = 2048

        # Initialize libusb context
        res = self._lib.libusb_init(ctypes.byref(self._ctx))
        if res != 0:
            raise OctoPlusError(f"Failed to initialize libusb: error {res}")

    def _setup_libusb_signatures(self):
        self._lib.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self._lib.libusb_init.restype = ctypes.c_int
        self._lib.libusb_exit.argtypes = [ctypes.c_void_p]
        self._lib.libusb_exit.restype = None

        self._lib.libusb_get_device_list.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)),
        ]
        self._lib.libusb_get_device_list.restype = ctypes.c_ssize_t
        self._lib.libusb_free_device_list.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int,
        ]
        self._lib.libusb_free_device_list.restype = None

        self._lib.libusb_get_device_descriptor.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._lib.libusb_get_device_descriptor.restype = ctypes.c_int

        self._lib.libusb_open.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._lib.libusb_open.restype = ctypes.c_int

        self._lib.libusb_close.argtypes = [ctypes.c_void_p]
        self._lib.libusb_close.restype = None

        self._lib.libusb_claim_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.libusb_claim_interface.restype = ctypes.c_int

        self._lib.libusb_release_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.libusb_release_interface.restype = ctypes.c_int

        self._lib.libusb_control_transfer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint16,
            ctypes.c_uint16,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint16,
            ctypes.c_uint,
        ]
        self._lib.libusb_control_transfer.restype = ctypes.c_int

        self._lib.libusb_bulk_transfer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_uint,
        ]
        self._lib.libusb_bulk_transfer.restype = ctypes.c_int

        self._lib.libusb_clear_halt.argtypes = [ctypes.c_void_p, ctypes.c_uint8]
        self._lib.libusb_clear_halt.restype = ctypes.c_int

        self._lib.libusb_strerror.argtypes = [ctypes.c_int]
        self._lib.libusb_strerror.restype = ctypes.c_char_p

    def _get_err_str(self, code: int) -> str:
        try:
            return self._lib.libusb_strerror(code).decode("utf-8", errors="replace")
        except Exception:
            return f"Error {code}"

    # -----------------------------------------------------------------------
    # Connection Lifecycle
    # -----------------------------------------------------------------------

    def open(self):
        """Open the camera and claim the primary USB interface."""
        if self._is_open:
            return

        dev_list = ctypes.POINTER(ctypes.c_void_p)()
        cnt = self._lib.libusb_get_device_list(self._ctx, ctypes.byref(dev_list))
        if cnt < 0:
            raise OctoPlusError(f"libusb_get_device_list failed: {self._get_err_str(cnt)}")

        target_dev = None
        matched_pid = None
        try:
            for i in range(cnt):
                dev = dev_list[i]
                desc = _DeviceDescriptor()
                if self._lib.libusb_get_device_descriptor(dev, ctypes.byref(desc)) == 0:
                    if desc.idVendor == self.vid:
                        if self.pid is not None:
                            if desc.idProduct == self.pid:
                                target_dev = dev
                                matched_pid = desc.idProduct
                                break
                        elif desc.idProduct in PRODUCT_IDS_OCTOPLUS:
                            target_dev = dev
                            matched_pid = desc.idProduct
                            break

            if target_dev is None:
                pid_str = f"PID 0x{self.pid:04X}" if self.pid else "any known OctoPlus PID"
                raise OctoPlusError(f"No e2v camera found matching VID 0x{self.vid:04X}, {pid_str}.")

            handle = ctypes.c_void_p(0)
            res = self._lib.libusb_open(target_dev, ctypes.byref(handle))
            if res != 0:
                raise OctoPlusError(
                    f"Failed to open camera device: {self._get_err_str(res)} "
                    f"(Check user permissions or udev rules for VID 0x{self.vid:04X}:PID 0x{matched_pid:04X})"
                )

            self._handle = handle
            self.pid = matched_pid

            # Claim interface 0
            res = self._lib.libusb_claim_interface(self._handle, 0)
            if res != 0:
                self._lib.libusb_close(self._handle)
                self._handle = None
                raise OctoPlusError(f"Failed to claim interface 0: {self._get_err_str(res)}")

            self._is_open = True
            time.sleep(0.01)

            # Query sensor width
            try:
                self._sensor_width = self.read_u32(REG_SENSOR_WIDTH)
            except Exception:
                self._sensor_width = 2048

        finally:
            self._lib.libusb_free_device_list(dev_list, 1)

    def close(self, stop_acquisition: bool = False):
        """Release interface and close the camera handle."""
        if self._handle:
            if stop_acquisition:
                try:
                    self.write_u32(REG_ACQUISITION_STOP, 0)
                except Exception:
                    pass
            try:
                self._lib.libusb_release_interface(self._handle, 0)
            except Exception:
                pass
            try:
                self._lib.libusb_close(self._handle)
            except Exception:
                pass
            self._handle = None
        self._is_open = False

    def __enter__(self) -> OctoPlusCamera:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
        if self._ctx:
            try:
                self._lib.libusb_exit(self._ctx)
            except Exception:
                pass
            self._ctx = None

    # -----------------------------------------------------------------------
    # Low-level Register Read / Write
    # -----------------------------------------------------------------------

    def check_firmware_status(self) -> int:
        """Query the internal FPGA status request code (0xB1). Returns 0 on OK."""
        if not self._is_open:
            raise OctoPlusError("Camera not open")

        buf = (ctypes.c_uint8 * 4)()
        res = self._lib.libusb_control_transfer(
            self._handle, BM_REQ_VENDOR_IN, REQ_GET_STATUS, 0, 0, buf, 4, 1000
        )
        if res < 0:
            raise OctoPlusError(f"Status check failed: {self._get_err_str(res)}")
        return struct.unpack("<I", bytes(buf))[0]

    def read_register(self, address: int, size: int = 4) -> bytes:
        """
        Read raw bytes from a camera register using vendor request 0xB3.
        Address high 16 bits map to wValue; low 16 bits map to wIndex.
        """
        if not self._is_open:
            raise OctoPlusError("Camera not open")

        buf = (ctypes.c_uint8 * size)()
        w_val = (address >> 16) & 0xFFFF
        w_idx = address & 0xFFFF

        res = self._lib.libusb_control_transfer(
            self._handle, BM_REQ_VENDOR_IN, REQ_READ_REG, w_val, w_idx, buf, size, 1000
        )
        time.sleep(0.005)  # 5ms inter-transfer stability margin

        if res != size:
            raise OctoPlusError(
                f"Read register 0x{address:08X} failed: requested {size}B, got {res}B "
                f"({self._get_err_str(res)})"
            )
        return bytes(buf)

    def write_register(self, address: int, data: bytes):
        """
        Write raw bytes to a camera register using vendor request 0xB2.
        Address high 16 bits map to wValue; low 16 bits map to wIndex.
        """
        if not self._is_open:
            raise OctoPlusError("Camera not open")

        size = len(data)
        buf = (ctypes.c_uint8 * size).from_buffer_copy(data)
        w_val = (address >> 16) & 0xFFFF
        w_idx = address & 0xFFFF

        res = self._lib.libusb_control_transfer(
            self._handle, BM_REQ_VENDOR_OUT, REQ_WRITE_REG, w_val, w_idx, buf, size, 1000
        )
        time.sleep(0.005)

        if res != size:
            raise OctoPlusError(
                f"Write register 0x{address:08X} failed: sent {size}B, got {res}B "
                f"({self._get_err_str(res)})"
            )

    def read_u32(self, address: int) -> int:
        """Read a 32-bit little-endian unsigned integer from a register."""
        data = self.read_register(address, 4)
        return struct.unpack("<I", data)[0]

    def write_u32(self, address: int, value: int):
        """Write a 32-bit little-endian unsigned integer to a register."""
        data = struct.pack("<I", value & 0xFFFFFFFF)
        self.write_register(address, data)

    def read_string(self, address: int, max_length: int = 64) -> str:
        """Read a null-terminated ASCII string from a register."""
        data = self.read_register(address, max_length)
        return data.decode("latin1", errors="replace").split("\x00", 1)[0].strip()

    # -----------------------------------------------------------------------
    # Camera Information & Status
    # -----------------------------------------------------------------------

    def get_device_info(self) -> Dict[str, Any]:
        """Query and return general camera identification details."""
        mfg = "e2v"
        model = "OCTOPUS1_USB"
        serial = ""

        try:
            mfg = self.read_string(REG_MANUFACTURER_NAME, 64) or mfg
        except Exception:
            pass

        try:
            model = self.read_string(REG_MODEL_NAME, 64) or model
        except Exception:
            pass

        try:
            serial = self.read_string(REG_SERIAL_NUMBER, 64)
        except Exception:
            pass

        fw_ver = "Unknown"
        try:
            fw_ver = self.read_string(REG_FIRMWARE_VERSION, 4)
        except Exception:
            pass

        return {
            "manufacturer": mfg,
            "model": model,
            "serial": serial,
            "firmware_version": fw_ver,
            "vid": f"0x{self.vid:04X}",
            "pid": f"0x{self.pid:04X}" if self.pid else "Unknown",
            "sensor_width": self._sensor_width,
        }

    def get_status_flags(self) -> CameraStatusFlags:
        """Read and parse the camera status bitmask flags."""
        raw_status = self.read_u32(REG_STATUS)
        return CameraStatusFlags(raw_status)

    # -----------------------------------------------------------------------
    # Timing & Trigger Configuration (Line Period, Exposure, Trigger Mode)
    # -----------------------------------------------------------------------

    def get_line_period(self) -> float:
        """Return current line period in microseconds (us)."""
        raw = self.read_u32(REG_LINE_PERIOD)
        return raw * 0.01

    def set_line_period(self, period_us: float):
        """Set line period in microseconds (us). Step is 0.01 us."""
        raw = int(round(period_us / 0.01))
        min_raw = self.read_u32(REG_LINE_PERIOD_MIN)
        if raw < min_raw:
            raise ValueError(
                f"Requested line period {period_us:.2f} us is below minimum {min_raw*0.01:.2f} us."
            )
        self.write_u32(REG_LINE_PERIOD, raw)

    def get_line_rate(self) -> float:
        """Return current line rate in Hertz (Hz)."""
        period_us = self.get_line_period()
        return 1e6 / period_us if period_us > 0 else 0.0

    def set_line_rate(self, rate_hz: float):
        """Set line rate in Hertz (Hz). Translates into line period in us."""
        if rate_hz <= 0:
            raise ValueError("Line rate must be positive.")
        period_us = 1e6 / rate_hz
        self.set_line_period(period_us)

    def get_line_period_min(self) -> float:
        """Return the hardware minimum line period in microseconds."""
        raw = self.read_u32(REG_LINE_PERIOD_MIN)
        return raw * 0.01

    def get_exposure_time(self) -> float:
        """Return current sensor exposure / integration time in microseconds (us)."""
        raw = self.read_u32(REG_EXPOSURE_TIME)
        return raw * 0.01

    def set_exposure_time(self, exposure_us: float):
        """Set sensor exposure time in microseconds (us). Step is 0.01 us."""
        raw = int(round(exposure_us / 0.01))
        min_raw = self.read_u32(REG_EXPOSURE_TIME_MIN)
        max_raw = self.read_u32(REG_EXPOSURE_TIME_MAX)

        if raw < min_raw or raw > max_raw:
            raise ValueError(
                f"Requested exposure {exposure_us:.2f} us is outside allowed range "
                f"[{min_raw*0.01:.2f} us, {max_raw*0.01:.2f} us]."
            )
        self.write_u32(REG_EXPOSURE_TIME, raw)

    def get_exposure_range(self) -> Tuple[float, float]:
        """Return (min_exposure_us, max_exposure_us)."""
        min_raw = self.read_u32(REG_EXPOSURE_TIME_MIN)
        max_raw = self.read_u32(REG_EXPOSURE_TIME_MAX)
        return (min_raw * 0.01, max_raw * 0.01)

    def get_trigger_mode(self) -> TriggerMode:
        """Return current trigger mode enumeration."""
        raw = self.read_u32(REG_TRIGGER_MODE)
        return TriggerMode(raw)

    def set_trigger_mode(self, mode: TriggerMode | int):
        """Set camera trigger mode (0 = Internal Free Run, 2 = External Line, etc.)."""
        val = int(mode)
        self.write_u32(REG_TRIGGER_MODE, val)

    def get_gpo_mode(self) -> GpoMode:
        """Return GPO (Pin 3 sync out) mode configuration."""
        raw = self.read_u32(REG_GPO_CONFIG)
        return GpoMode(raw)

    def set_gpo_mode(self, mode: GpoMode | int):
        """Set GPO (Pin 3 sync out) mode. Default 0x2E = exposure pulse."""
        self.write_u32(REG_GPO_CONFIG, int(mode))

    def pulse_sync_out(
        self,
        duration_ms: float = 10.0,
        high_val: Optional[int] = None,
        low_val: Optional[int] = None,
    ):
        """
        Emit a single manual pulse on Hirose Pin 3 (GPO).
        Steers external MUX pulser boxes (CD4017 decade counter) to advance
        by exactly one phase (e.g. Dark -> 808nm -> 980nm -> Dark)
        without activating continuous streaming or line acquisition.

        By default, toggles the GPO configuration register (0x122FC) between
        inverted polarity (0x2F) and normal idle (0x2E) for the specified
        duration, providing a clean hardware clock edge on Pin 3.
        """
        orig_gpo = self.read_u32(REG_GPO_CONFIG)
        if high_val is None:
            # 0x2E has bit 0 = 0. Toggling bit 0 (0x2F) inverts the polarity
            # causing the idle line to transition from LOW to HIGH.
            high_val = 0x2F if orig_gpo == 0x2E else (orig_gpo ^ 0x01)
        if low_val is None:
            low_val = orig_gpo

        # 1. Drive HIGH
        self.write_u32(REG_GPO_CONFIG, high_val)
        time.sleep(max(0.001, duration_ms / 1000.0))
        # 2. Drive LOW / restore
        self.write_u32(REG_GPO_CONFIG, low_val)

    # -----------------------------------------------------------------------
    # Image Geometry & Processing
    # -----------------------------------------------------------------------

    def get_pixel_format(self) -> PixelFormat:
        """Return sensor bit depth format."""
        return PixelFormat(self.read_u32(REG_PIXEL_FORMAT))

    def set_pixel_format(self, fmt: PixelFormat | int):
        """Set sensor bit depth (2: Mono10, 3: Mono11, 4: Mono12)."""
        self.write_u32(REG_PIXEL_FORMAT, int(fmt))

    def get_analog_gain(self) -> AnalogGain:
        """Return pre-amplifier analog gain setting."""
        return AnalogGain(self.read_u32(REG_ANALOG_GAIN))

    def set_analog_gain(self, gain: AnalogGain | int):
        """Set analog pre-amplifier gain (0: x1, 1: x2, 2: x4)."""
        self.write_u32(REG_ANALOG_GAIN, int(gain))

    def get_digital_gain(self) -> int:
        """Return digital gain (0 to 1791)."""
        return self.read_u32(REG_DIGITAL_GAIN)

    def set_digital_gain(self, gain: int):
        """Set digital gain (0 = x1.0 up to 1791 = x7.996)."""
        if not (0 <= gain <= 1791):
            raise ValueError("Digital gain must be between 0 and 1791.")
        self.write_u32(REG_DIGITAL_GAIN, gain)

    def get_digital_offset(self) -> int:
        """Return digital offset."""
        raw = self.read_u32(REG_DIGITAL_OFFSET)
        # 32-bit signed integer
        return struct.unpack("<i", struct.pack("<I", raw))[0]

    def set_digital_offset(self, offset: int):
        """Set digital offset (-4096 to 4095)."""
        if not (-4096 <= offset <= 4095):
            raise ValueError("Digital offset must be between -4096 and 4095.")
        raw = struct.unpack("<I", struct.pack("<i", offset))[0]
        self.write_u32(REG_DIGITAL_OFFSET, raw)

    def get_test_pattern(self) -> TestPattern:
        """Return active FPGA test pattern."""
        return TestPattern(self.read_u32(REG_TEST_PATTERN))

    def set_test_pattern(self, pattern: TestPattern | int):
        """Set FPGA test pattern (0 = Sensor, 1 = Horizontal Ramp, etc.)."""
        self.write_u32(REG_TEST_PATTERN, int(pattern))

    # -----------------------------------------------------------------------
    # Acquisition & Hardware Trigger Sync Out Control
    # -----------------------------------------------------------------------

    def flush_buffers(self):
        """Flush camera internal FIFO / buffers."""
        self.write_u32(REG_FLUSH_BUFFER, 0)

    def start_acquisition(self):
        """
        Start camera acquisition.
        This immediately starts line integration and activates the hardware
        trigger sync out pulses on Pin 3 (GPO) of the Hirose connector.
        """
        self.flush_buffers()
        self.write_u32(REG_ACQUISITION_START, 0)

    def stop_acquisition(self):
        """Stop camera acquisition. Halts sensor integration and sync out pulses."""
        self.write_u32(REG_ACQUISITION_STOP, 0)

    def is_acquisition_running(self) -> bool:
        """Check if acquisition is currently active on the camera."""
        flags = self.get_status_flags()
        return bool(flags & CameraStatusFlags.ACQUISITION_RUNNING)

    def drain_stream_chunk(self, buffer_size: int = 65536, timeout_ms: int = 100) -> int:
        """
        Read and discard one chunk from the USB bulk endpoint.
        Used to keep the USB stream clear while acquisition and sync out run continuously.
        """
        buf = (ctypes.c_uint8 * buffer_size)()
        transferred = ctypes.c_int(0)
        res = self._lib.libusb_bulk_transfer(
            self._handle, EP_STREAM_IN, buf, buffer_size, ctypes.byref(transferred), timeout_ms
        )
        return transferred.value if res == 0 else 0

    def snap(self, num_bytes: int = 65536, timeout_ms: int = 2000) -> bytes:
        """
        Acquire a snapshot chunk of raw line data from Endpoint 0x83.
        Starts acquisition if not already active, reads the data, and stops acquisition.
        """
        was_running = self.is_acquisition_running()
        if not was_running:
            self.start_acquisition()

        buf = (ctypes.c_uint8 * num_bytes)()
        transferred = ctypes.c_int(0)
        try:
            res = self._lib.libusb_bulk_transfer(
                self._handle, EP_STREAM_IN, buf, num_bytes, ctypes.byref(transferred), timeout_ms
            )
            if res != 0:
                raise OctoPlusError(f"Bulk transfer failed: {self._get_err_str(res)}")
            return bytes(buf[:transferred.value])
        finally:
            if not was_running:
                self.stop_acquisition()


def unpack_mono12p(data: bytes, width: int = 2048) -> list[list[int]]:
    """
    Unpack standard USB3 Vision Mono12p packed bytes (3 bytes -> 2 pixels)
    into a list of lines [num_lines][width], where each pixel value is in [0..4095].
    Automatically skips the 16-byte U3VL header if present.
    """
    offset = 0
    if len(data) >= 16 and data[:4] == b"U3VL":
        offset = 16

    payload = data[offset:]
    line_stride = (width * 3) // 2  # 3072 bytes per 2048-pixel line
    num_lines = len(payload) // line_stride

    lines = []
    for l_idx in range(num_lines):
        line_start = l_idx * line_stride
        line_data = payload[line_start : line_start + line_stride]
        pixels = []
        for i in range(0, line_stride, 3):
            b0 = line_data[i]
            b1 = line_data[i + 1]
            b2 = line_data[i + 2]
            p0 = b0 | ((b1 & 0x0F) << 8)
            p1 = (b1 >> 4) | (b2 << 4)
            pixels.extend((p0, p1))
        lines.append(pixels[:width])
    return lines
