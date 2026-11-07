# pyoctoplus

Clean-room, cross-platform Python driver and CLI for **Teledyne e2v OctoPlus USB 3.0** line scan cameras.

Communicates natively over USB 3.0 using `libusb-1.0`. No proprietary SDK, kernel modules, or manufacturer runtime installers required.

## Features

- **Hardware Configuration**: Set exposure time, line rate/period, digital/analog gain, offset, and trigger modes.
- **Hardware Trigger Sync Out**: Start acquisition to drive external timing / laser sync out pulses via Hirose connector Pin 3 (GPO).
- **Cross-Platform**: Works identically across Linux (`libusb-1.0.so`), Windows (`libusb-1.0.dll`), and macOS (`libusb-1.0.dylib`).
- **Data Capture**: Stream raw lines and capture line scan buffers directly into Python/NumPy arrays.

## Linux Setup

Install the udev permissions rule:

```bash
sudo cp udev/99-e2v-octoplus.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Installation

```bash
pip install -e .
```

## CLI Usage

```bash
# Query camera identification, status, and current timings
octoplus-cli --info

# Configure line rate and exposure time
octoplus-cli --rate 20000 --exposure 30

# Start acquisition to activate hardware trigger sync out
octoplus-cli --start

# Keep acquisition running (sync out active until Ctrl+C)
octoplus-cli --run

# Stop acquisition
octoplus-cli --stop
```

## License

MIT
