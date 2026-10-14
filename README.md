# KL200-pyhton
Python library for the XKC-KL200-2M-UART laser distance sensor (via pyserial).

Developed by Tobias Baumann (aka Raptorsds) and ChatGPT with input based on the XKC-KL-200 PDF version 10 from 2023.
The library was reviewed and optimized with [Claude Code](https://claude.com/claude-code) in October 2026, based on the XKC instruction manual (see changelog below).

Note: This project is not associated with XKC. This project is version 2 Beta and has not yet been fully tested on real hardware.

## Overview

This library communicates with the XKC-KL200 laser distance sensor over UART using `pyserial`
(PC, Raspberry Pi, etc.). It supports all configuration commands from the datasheet, manual
distance requests and the automatic upload mode.

The previous versions are kept in `src/archiv/`:
- `XKC_KL200.py` – original MicroPython version (`machine.UART`)
- `XKC_KL200_20261014.py` – pyserial version before the 2026-10-14 optimization

## Features

- Change sensor address
- Change baud rate (optionally switches the local port as well)
- Set upload mode (manual/automatic)
- Set upload interval
- Set LED mode
- Set relay mode
- Set communication mode (UART/Relay)
- Set response speed (high precision / normal / high stability)
- Read current configuration
- Read distance (manual and automatic mode)
- Restore factory settings (hard reset) or user settings (soft reset)
- Robust frame handling: resynchronisation, XOR8 checksum and ACK (`0x66`) check

## Installation

```bash
pip install pyserial
```

Copy `src/XKC_KL200.py` into your project.

## Wiring

| Wire   | Function                                    |
|--------|---------------------------------------------|
| Brown  | VCC 5–24 V                                  |
| Yellow | TX of the sensor → RX of the controller (1 kΩ pull-up to the controller's VCC) |
| Blue   | GND                                         |
| Black  | RX of the sensor ← TX of the controller     |

Default serial settings: 9600 baud, 8 data bits, no parity, 1 stop bit.

## Usage

### Manual mode

```python
from XKC_KL200 import XKC_KL200, XKC_KL200_Error

with XKC_KL200('/dev/ttyUSB0', baudrate=9600) as sensor:
    sensor.set_communication_mode(1)      # UART mode
    sensor.set_upload_mode(False)         # manual query mode

    distance = sensor.read_distance()
    if distance is None:
        print("No answer from sensor")
    else:
        print("Distance:", distance, "mm")
```

### Automatic mode

```python
import time
from XKC_KL200 import XKC_KL200, XKC_KL200_Error

with XKC_KL200('/dev/ttyUSB0') as sensor:
    if sensor.set_upload_mode(True) != XKC_KL200_Error.SUCCESS:
        print("Could not set upload mode")
    sensor.set_upload_interval(5)         # 5 x 100 ms = 500 ms

    while True:
        if sensor.available():
            print("Distance:", sensor.get_distance(), "mm")
        time.sleep(0.01)
```

See `src/example.py` for a complete example.

## API

All configuration methods return an `XKC_KL200_Error`:
`SUCCESS`, `INVALID_PARAMETER`, `TIMEOUT`, `CHECKSUM_ERROR` or `RESPONSE_ERROR`.

| Method | Description |
|--------|-------------|
| `XKC_KL200(port, baudrate=9600, timeout=1.0, address=0xFFFF)` | Opens the serial port. `address` 0xFFFF = broadcast. Usable as context manager (`with`). |
| `close()` | Closes the serial port. |
| `hard_reset()` | Restores the XKC factory configuration (0xFE). |
| `soft_reset()` | Restores the user default configuration (0xFD). |
| `change_address(address)` | Sets the device address (0–65534). |
| `change_baud_rate(index, apply=True)` | 0=2400, 1=4800, 2=9600, 3=14400, 4=19200, 5=38400, 6=56000, 7=57600, 8=115200, 9=128000. With `apply=True` the local port is switched too. |
| `set_upload_mode(auto_upload)` | `True` = automatic upload, `False` = manual query. |
| `set_upload_interval(interval)` | 1–100 (steps of 100 ms → 100 ms–10 s). |
| `set_led_mode(mode)` | 0=on when detected, 1=off when detected, 2=always off, 3=always on. |
| `set_relay_mode(mode)` | 0=active when detected, 1=inactive when detected (relay mode only). |
| `set_communication_mode(mode)` | 0=relay mode, 1=UART mode. |
| `set_response_speed(mode)` | 0=high precision, 1=normal, 2=high stability. |
| `read_config()` | Returns a `dict` with the current configuration or `None`. |
| `read_distance(timeout=None)` | Distance in mm or `None` on timeout/error. In automatic mode returns the latest received value. |
| `available()` | `True` if a new distance value is available. |
| `process_auto_data()` | Processes all received frames; `True` if a new distance was received. |
| `get_distance()` | Returns the last distance and resets `available()`. |
| `get_last_received_distance()` | Returns the last distance without resetting `available()`. |

## Notes on the datasheet

- The datasheet contradicts itself on the upload mode (page 4: 0=auto; page 10: 1=auto).
  This library uses **1 = automatic** as in the command table.
- The upload interval is a decimal value in 100 ms steps: 1 s = `10` (`0x0A`), not `0x10`.
- The line-mode command is sent as `0x61 0x30`, the sensor answers with `0x62 0x30`.

## Changelog

### 2026-10-14 – optimized with Claude Code
- Fixed: the file ended in the middle of `def _wait_for_response` (SyntaxError, module could not be imported).
- `_wait_for_response` implemented: checks ACK byte `0x66` and returns `SUCCESS`, `TIMEOUT`, `CHECKSUM_ERROR` or `RESPONSE_ERROR`.
- Receive buffer with frame resynchronisation, length and XOR8 checksum check instead of a blind `read(9)`.
- Distance frames that arrive between a command and its ACK (automatic mode) are processed instead of being mistaken for the answer.
- `set_upload_mode` only switches the internal mode after the sensor confirmed it.
- `read_distance` returns `None` on timeout/error instead of a stale value.
- New: `read_config()`, `set_response_speed()`, `address` parameter, context manager, `apply` for `change_baud_rate`.
- Parameter checks also reject negative values.
- `example.py`: import fixed (`XKC_KL200` instead of `xkc_kl200`).
