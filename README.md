# pyoctoplus

Clean-room, cross-platform Python driver and CLI for **Teledyne e2v OctoPlus USB 3.0** line scan cameras.

Communicates natively over USB 3.0 using `libusb-1.0`. No proprietary SDK, kernel modules, or manufacturer runtime installers required.

## Features

- **Hardware Configuration**: Set exposure time, line rate/period, digital/analog gain, offset, and trigger modes.
- **Hardware Trigger Sync Out**: Start acquisition to drive external timing / laser sync out pulses via Hirose connector Pin 3 (GPO).
- **Cross-Platform**: Works identically across Linux (`libusb-1.0.so`), Windows (`libusb-1.0.dll`), and macOS (`libusb-1.0.dylib`).
- **Data Capture**: Stream raw lines and capture line scan buffers directly into Python/NumPy arrays.

## Linux Setup

Run the helper script to install the udev rules and configure non-root access:

```bash
sudo ./install_udev.sh
```

Or manually:

```bash
sudo cp udev/99-e2v-octoplus.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Hirose HR10A Connector Pinout (Rear Panel)

| Pin | Signal | Description |
| :---: | :---: | :--- |
| **1** | **PWR** | Power supply (6V – 15V DC, optional if USB3 bus-powered) |
| **2** | **GPO2** | Auxiliary General Purpose Output |
| **3** | **GPO1** | **Hardware Trigger Sync Out** (Exposure / Integration pulse) |
| **4** | **GND** | Power & Signal Ground |
| **5** | **GPI2** | Auxiliary General Purpose Input |
| **6** | **GPI1** | External Hardware Trigger In |

## Installation & Running

You can run the launcher directly without installation:

```bash
./octoplus-cli --help
```

Or install in your Python environment:

```bash
pip install -e .
```

## CLI Usage

```bash
# Query camera status, model, firmware, serial, and active timings
./octoplus-cli --info

# Configure line rate and exposure time
./octoplus-cli --rate 25000 --exposure 30

# Enable FPGA horizontal ramp test pattern (0 = sensor, 1 = ramp)
./octoplus-cli --pattern 1

# Start acquisition (Hirose Pin 3 sync out pulses activate)
./octoplus-cli --start

# Stop acquisition
./octoplus-cli --stop

# Emit a single hardware trigger pulse on Hirose Pin 3 (steps MUX phase without streaming)
./octoplus-cli --pulse
./octoplus-cli --pulse --pulse-ms 20

# Continuous acquisition stream monitor (displays live MB/s until Ctrl+C)
./octoplus-cli --run

# Capture a snapshot buffer directly to NumPy 2D array or raw bytes
./octoplus-cli --snap test.npy
./octoplus-cli --snap test.raw
```

## License

MIT
