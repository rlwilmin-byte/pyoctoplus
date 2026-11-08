"""
pyoctoplus: Open cross-platform Python driver and CLI for Teledyne e2v OctoPlus USB 3.0 line cameras.
"""

from pyoctoplus.camera import OctoPlusCamera, OctoPlusError, unpack_mono12p
from pyoctoplus.registers import (
    TriggerMode,
    PixelFormat,
    AnalogGain,
    TestPattern,
    GpoMode,
    CameraStatusFlags,
)

__version__ = "0.1.0"

__all__ = [
    "OctoPlusCamera",
    "OctoPlusError",
    "unpack_mono12p",
    "TriggerMode",
    "PixelFormat",
    "AnalogGain",
    "TestPattern",
    "GpoMode",
    "CameraStatusFlags",
]
