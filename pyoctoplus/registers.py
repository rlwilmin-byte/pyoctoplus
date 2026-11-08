"""
Hardware register addresses, USB identifiers, and enumerations for
Teledyne e2v OctoPlus USB 3.0 line scan cameras.
"""

from enum import IntEnum, IntFlag

# USB Vendor and Product Identifiers
VENDOR_ID_E2V = 0x0FD3
PRODUCT_IDS_OCTOPLUS = (
    0x0616,  # OCTOPUS1_USB / iCMOS OCT USB3
    0x0F0D,  # Camera OCT USB3 Gen1
    0x0615,  # Camera OCT USB3 Gen2
    0x0611,  # Prox Onyx USB3
)

# USB Endpoint and Control Request Codes
EP_CONTROL = 0x00
EP_STREAM_IN = 0x83

BM_REQ_VENDOR_OUT = 0x40  # Host-to-Device | Vendor | Device
BM_REQ_VENDOR_IN = 0xC0   # Device-to-Host | Vendor | Device

REQ_GET_STATUS = 0xB1
REQ_WRITE_REG = 0xB2
REQ_READ_REG = 0xB3

# USB3 Vision Stream Packet Magic
U3V_LEADER_MAGIC = b"U3VL"
U3V_TRAILER_MAGIC = b"U3VT"

# ---------------------------------------------------------------------------
# Camera Register Addresses
# ---------------------------------------------------------------------------

# Device Identification (Strings)
REG_MANUFACTURER_NAME = 0x00000004
REG_MODEL_NAME = 0x00000044
REG_FAMILY_NAME = 0x00000084
REG_DEVICE_VERSION = 0x000000C4
REG_MANUFACTURER_INFO = 0x00000104
REG_SERIAL_NUMBER = 0x00000144
REG_USER_DEFINED_NAME = 0x00000184
REG_FIRMWARE_VERSION = 0x00016040

# Acquisition & State Control
REG_STATUS = 0x00012000
REG_ACQUISITION_START = 0x00018000
REG_ACQUISITION_STOP = 0x00018004
REG_FLUSH_BUFFER = 0x00012290
REG_REBOOT_CAMERA = 0x00018100

# Image Geometry & Pixel Format
REG_SENSOR_WIDTH = 0x00012004
REG_ROI_WIDTH = 0x00020030
REG_PIXEL_FORMAT = 0x00012020
REG_REVERSE_READING = 0x00012024
REG_TEST_PATTERN = 0x00012080
REG_TEST_IMAGE_HEIGHT = 0x00012084
REG_TEST_IMAGE_CONSTANT = 0x00012088

# Host/Virtual Acquisition Registers
REG_CONTEXT_DATA_ENABLE = 0x4F000000
REG_PAYLOAD_SIZE = 0x4F000004
REG_LINE_PITCH = 0x4F000008
REG_IMAGE_HEIGHT = 0x4F00000C

# Integration, Timing & Trigger Controls (0.01 us steps)
REG_LINE_PERIOD = 0x00012100
REG_LINE_PERIOD_MIN = 0x00012104
REG_EXPOSURE_TIME = 0x00012108
REG_TRIGGER_MODE = 0x0001210C
REG_TRIGGER_MISSED = 0x00012110
REG_EXPOSURE_TIME_MIN = 0x00012114
REG_EXPOSURE_TIME_MAX = 0x00012118
REG_LINE_FRAME_FILTER_DURATION = 0x0001211C
REG_GPI_FORMAT = 0x00012120
REG_TRIGGER_JITTER = 0x00012184
REG_LINE_COUNTER_RESET = 0x00012288
REG_GPO_CONFIG = 0x000122FC

# Gain, Offset & Flat-Field Correction
REG_ANALOG_GAIN = 0x00012200
REG_DIGITAL_GAIN = 0x00012204
REG_DIGITAL_OFFSET = 0x0001220C
REG_FFC_ENABLE = 0x00012300

# User Set Configuration Banks
REG_USERSET_LOAD = 0x00017000
REG_USERSET_SAVE = 0x00017004


class TriggerMode(IntEnum):
    """Camera line and frame trigger modes (Register 0x1210C)."""
    INTERNAL_PROGRAMMABLE = 0          # Free-run: internal line trigger, programmable exposure & period
    INTERNAL_MAX_EXPOSURE = 1          # Free-run: internal line trigger, max exposure & programmable period
    EXTERNAL_LINE_PROGRAMMABLE = 2     # External line trigger, programmable exposure
    EXTERNAL_LINE_MAX_EXPOSURE = 3     # External line trigger, maximum exposure
    EXTERNAL_MIXED_PROGRAMMABLE = 4    # External mixed line & frame trigger, programmable exposure
    EXTERNAL_MIXED_MAX_EXPOSURE = 5    # External mixed line & frame trigger, maximum exposure
    EXTERNAL_FRAME_INTERNAL_LINE = 6   # External frame trigger + internal line trigger, programmable exposure
    EXTERNAL_FRAME_MAX_EXPOSURE = 7    # External frame trigger + internal line trigger, max exposure


class PixelFormat(IntEnum):
    """Sensor output bit depth (Register 0x12020)."""
    MONO10 = 2
    MONO11 = 3
    MONO12 = 4


class AnalogGain(IntEnum):
    """Pre-amplifier analog gain setting (Register 0x12200)."""
    GAIN_1X = 0
    GAIN_2X = 1
    GAIN_4X = 2


class TestPattern(IntEnum):
    """Internal FPGA test pattern selector (Register 0x12080)."""
    OFF = 0
    GREY_HORIZONTAL_RAMP = 1
    GREY_VERTICAL_RAMP = 2
    GREY_DIAGONAL_RAMP = 3
    MOVING_HORIZONTAL_RAMP = 4
    MOVING_VERTICAL_RAMP = 5
    MOVING_DIAGONAL_RAMP = 6
    CHECKERBOARD = 7
    HORIZONTAL_LINES = 8
    VERTICAL_LINES = 9
    CONSTANT = 10


class GpoMode(IntEnum):
    """GPO (Pin 3 sync out) behavior configuration (Register 0x122FC)."""
    EXPOSURE_PULSE = 0x2E       # Default: outputs pulse at each sensor line exposure
    MISSED_LINE_TRIGGER = 0x32  # Outputs pulse when external line trigger is missed
    MISSED_FRAME_TRIGGER = 0x4A # Outputs pulse when external frame trigger is missed


class CameraStatusFlags(IntFlag):
    """Bitmask flags for Camera Status register (0x12000)."""
    TRIGGER_TIMEOUT = 1 << 0       # No trigger for > 1s
    TRIGGER_TOO_FAST = 1 << 1      # Trigger frequency exceeds limit
    ACQUISITION_RUNNING = 1 << 4   # Acquisition currently active
    DATA_OVERFLOW = 1 << 5         # FPGA FIFO overflow
    FFC_OVERFLOW = 1 << 8          # Overflow during FFC calibration
    FFC_UNDERFLOW = 1 << 9         # Underflow during FFC calibration
    FFC_ERROR = 1 << 10            # Error during FFC calibration
    INITIALIZING = 1 << 15         # Camera under initialization
    HARDWARE_ERROR = 1 << 16       # Hardware fault detected
