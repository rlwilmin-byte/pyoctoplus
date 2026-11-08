"""
Command-line interface for the pyoctoplus driver.
Provides camera configuration, status queries, and trigger sync out activation.
"""

from __future__ import annotations

import argparse
import sys
import time
import signal

from pyoctoplus.camera import OctoPlusCamera, OctoPlusError
from pyoctoplus.registers import (
    TriggerMode,
    AnalogGain,
    TestPattern,
    GpoMode,
    CameraStatusFlags,
)


def _format_status(cam: OctoPlusCamera):
    info = cam.get_device_info()
    status_flags = cam.get_status_flags()
    is_running = cam.is_acquisition_running()

    try:
        period_us = cam.get_line_period()
        rate_hz = cam.get_line_rate()
    except Exception:
        period_us, rate_hz = 0.0, 0.0

    try:
        min_period_us = cam.get_line_period_min()
    except Exception:
        min_period_us = 0.0

    try:
        exp_us = cam.get_exposure_time()
        exp_min, exp_max = cam.get_exposure_range()
    except Exception:
        exp_us, exp_min, exp_max = 0.0, 0.0, 0.0

    trig_mode = cam.get_trigger_mode()
    gpo_mode = cam.get_gpo_mode()
    gain = cam.get_analog_gain()
    dig_gain = cam.get_digital_gain()
    offset = cam.get_digital_offset()
    pattern = cam.get_test_pattern()

    print("=" * 60)
    print(f"  e2v OctoPlus Camera Status & Configuration")
    print("=" * 60)
    print(f"  Model:            {info['model']}")
    print(f"  Serial:           {info['serial'] or 'N/A'}")
    print(f"  Firmware:         v{info['firmware_version']}")
    print(f"  USB ID:           {info['vid']}:{info['pid']}")
    print(f"  Sensor Width:     {info['sensor_width']} pixels")
    print("-" * 60)
    print(f"  Acquisition:      {'ACTIVE (Pulsing Sync Out)' if is_running else 'STOPPED'}")
    if rate_hz > 0:
        print(f"  Line Rate:        {rate_hz:,.1f} Hz  (Period: {period_us:.2f} µs | Min: {min_period_us:.2f} µs)")
        print(f"  Exposure Time:    {exp_us:.2f} µs  (Allowed: [{exp_min:.2f} µs .. {exp_max:.2f} µs])")
    else:
        print(f"  Line Rate:        [Acquisition running - timings locked]")
    print(f"  Trigger Mode:     {trig_mode.name} ({int(trig_mode)})")
    print(f"  GPO Sync Mode:    {gpo_mode.name} (0x{int(gpo_mode):02X}) -> Pin 3 of Hirose connector")
    print(f"  Analog Gain:      {gain.name} ({int(gain)})")
    print(f"  Digital Gain:     {dig_gain}")
    print(f"  Digital Offset:   {offset}")
    print(f"  Test Pattern:     {pattern.name} ({int(pattern)})")
    print(f"  Status Flags:     0x{int(status_flags):08X}")
    for flag in CameraStatusFlags:
        if flag and (status_flags & flag):
            print(f"    - {flag.name}")
    print("=" * 60)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="octoplus-cli",
        description="CLI control and trigger sync out activation for Teledyne e2v OctoPlus USB 3.0 cameras.",
    )

    # Actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--info", "-i",
        action="store_true",
        help="Query and display camera status and parameters.",
    )
    action_group.add_argument(
        "--start",
        action="store_true",
        help="Start camera acquisition (activates hardware trigger sync out).",
    )
    action_group.add_argument(
        "--stop",
        action="store_true",
        help="Stop camera acquisition (halts sync out pulses).",
    )
    action_group.add_argument(
        "--run",
        action="store_true",
        help="Run acquisition continuously in the foreground (sync out active until Ctrl+C).",
    )
    action_group.add_argument(
        "--snap",
        metavar="FILE",
        nargs="?",
        const="snap.raw",
        help="Acquire a test data chunk (default: snap.raw) and display summary.",
    )

    # Settings
    parser.add_argument(
        "--rate", "-r",
        type=float,
        help="Set line rate in Hertz (e.g. 20000 for 20 kHz).",
    )
    parser.add_argument(
        "--period", "-p",
        type=float,
        help="Set line period in microseconds (e.g. 50.0).",
    )
    parser.add_argument(
        "--exposure", "-e",
        type=float,
        help="Set exposure time in microseconds (e.g. 30.0).",
    )
    parser.add_argument(
        "--trigger", "-t",
        type=int,
        choices=[m.value for m in TriggerMode],
        help="Set trigger mode (0: Internal Free-run, 2: External Line, etc.).",
    )
    parser.add_argument(
        "--gpo",
        type=lambda x: int(x, 0),
        help="Set GPO sync out mode (e.g. 0x2E for exposure pulse on Pin 3).",
    )
    parser.add_argument(
        "--gain",
        type=int,
        choices=[0, 1, 2],
        help="Set pre-amp analog gain (0: 1x, 1: 2x, 2: 4x).",
    )
    parser.add_argument(
        "--pattern",
        type=int,
        choices=[p.value for p in TestPattern],
        help="Set internal test pattern (0: Sensor, 1: Horizontal Ramp, 7: Checkerboard).",
    )

    args = parser.parse_args(argv)

    try:
        cam = OctoPlusCamera()
        cam.open()
    except OctoPlusError as e:
        print(f"Error opening camera: {e}", file=sys.stderr)
        return 1

    try:
        # Apply any requested settings
        settings_changed = False

        if args.period is not None:
            cam.set_line_period(args.period)
            print(f"[OK] Set line period to {args.period:.2f} µs ({cam.get_line_rate():,.1f} Hz)")
            settings_changed = True
        elif args.rate is not None:
            cam.set_line_rate(args.rate)
            print(f"[OK] Set line rate to {args.rate:,.1f} Hz (Period: {cam.get_line_period():.2f} µs)")
            settings_changed = True

        if args.exposure is not None:
            cam.set_exposure_time(args.exposure)
            print(f"[OK] Set exposure time to {args.exposure:.2f} µs")
            settings_changed = True

        if args.trigger is not None:
            cam.set_trigger_mode(args.trigger)
            print(f"[OK] Set trigger mode to {TriggerMode(args.trigger).name} ({args.trigger})")
            settings_changed = True

        if args.gpo is not None:
            cam.set_gpo_mode(args.gpo)
            print(f"[OK] Set GPO mode to 0x{args.gpo:02X}")
            settings_changed = True

        if args.gain is not None:
            cam.set_analog_gain(args.gain)
            print(f"[OK] Set analog gain to {AnalogGain(args.gain).name}")
            settings_changed = True

        if args.pattern is not None:
            cam.set_test_pattern(args.pattern)
            print(f"[OK] Set test pattern to {TestPattern(args.pattern).name}")
            settings_changed = True

        # Perform action
        if args.start:
            rate = cam.get_line_rate()
            exp = cam.get_exposure_time()
            cam.start_acquisition()
            print("[OK] Acquisition STARTED. Hardware trigger sync out is ACTIVE on Hirose Pin 3.")
            print(f"     Line rate: {rate:,.1f} Hz | Exposure: {exp:.2f} µs")

        elif args.stop:
            cam.stop_acquisition()
            print("[OK] Acquisition STOPPED. Hardware trigger sync out is INACTIVE.")

        elif args.run:
            rate = cam.get_line_rate()
            exp = cam.get_exposure_time()
            print("[OK] Starting continuous acquisition...")
            cam.start_acquisition()
            print(f"     Sync out active on Pin 3 @ {rate:,.1f} Hz ({1e6/rate:.2f} µs period, {exp:.2f} µs pulse)")
            print("     Draining USB stream. Press Ctrl+C to stop.\n")

            running = True
            def _sig_handler(sig, frame):
                nonlocal running
                running = False
            signal.signal(signal.SIGINT, _sig_handler)

            total_bytes = 0
            start_time = time.time()
            last_report = start_time

            try:
                while running:
                    chunk_bytes = cam.drain_stream_chunk(buffer_size=65536, timeout_ms=100)
                    total_bytes += chunk_bytes
                    now = time.time()
                    if now - last_report >= 1.0:
                        elapsed = now - start_time
                        mb_sec = (total_bytes / (1024 * 1024)) / elapsed
                        sys.stdout.write(
                            f"\r[RUNNING] Elapsed: {elapsed:5.1f}s | Throughput: {mb_sec:5.1f} MB/s | Sync Out: ACTIVE"
                        )
                        sys.stdout.flush()
                        last_report = now
            finally:
                print("\n[OK] Stopping acquisition...")
                cam.stop_acquisition()
                print("[OK] Acquisition stopped.")

        elif args.snap:
            filename = args.snap
            print(f"Acquiring snapshot chunk (64 KB)...")
            raw_data = cam.snap(num_bytes=65536)
            with open(filename, "wb") as f:
                f.write(raw_data)
            print(f"[OK] Saved {len(raw_data):,} bytes to {filename}")

            # Inspect first pixels if payload data is present
            if len(raw_data) >= 64:
                import struct
                # Unpack 16-bit words (little-endian)
                num_words = min(16, len(raw_data) // 2)
                words = struct.unpack(f"<{num_words}H", raw_data[:num_words*2])
                print(f"     First {num_words} raw words: {words}")

        else:
            # Default action: show status
            _format_status(cam)

        return 0

    except Exception as e:
        print(f"Error during execution: {e}", file=sys.stderr)
        return 1
    finally:
        cam.close()


if __name__ == "__main__":
    sys.exit(main())
