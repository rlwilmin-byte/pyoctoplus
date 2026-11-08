#!/usr/bin/env python3
"""
Minimal example demonstrating how to configure line rate and exposure time,
and activate hardware trigger sync out on Hirose connector Pin 3 (GPO).
"""

import sys
import os
import time

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyoctoplus import OctoPlusCamera, TriggerMode, GpoMode


def main():
    print("Connecting to e2v OctoPlus camera...")
    with OctoPlusCamera() as cam:
        info = cam.get_device_info()
        print(f"Connected to {info['model']} (Serial: {info['serial'] or 'N/A'}, FW: v{info['firmware_version']})")

        # 1. Configure timing
        LINE_RATE_HZ = 20000.0  # 20 kHz (50 µs period)
        EXPOSURE_US = 30.0      # 30 µs integration

        print(f"Setting line rate to {LINE_RATE_HZ:,.1f} Hz...")
        cam.set_line_rate(LINE_RATE_HZ)

        print(f"Setting exposure time to {EXPOSURE_US:.2f} µs...")
        cam.set_exposure_time(EXPOSURE_US)

        # 2. Trigger mode: Internal free-run (0)
        cam.set_trigger_mode(TriggerMode.INTERNAL_PROGRAMMABLE)

        # 3. GPO mode: Exposure pulse on Pin 3 (0x2E)
        cam.set_gpo_mode(GpoMode.EXPOSURE_PULSE)

        # 4. Start acquisition -> hardware sync out pulses begin immediately
        print("\nStarting acquisition -> Hardware trigger sync out ACTIVE on Pin 3!")
        cam.start_acquisition()

        print("Pulsing sync out for 5 seconds (measuring USB stream)...")
        start = time.time()
        while time.time() - start < 5.0:
            cam.drain_stream_chunk(65536, 100)
            time.sleep(0.01)

        print("Stopping acquisition...")
        cam.stop_acquisition()
        print("Done. Hardware sync out halted.")


if __name__ == "__main__":
    main()
