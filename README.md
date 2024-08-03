# KL200-pyhton
MicroPhython library for XKC-Kl200 laser distance sensor


## Overview

This library provides support for the XKC-KL200 laser distance sensor using MicroPython. It allows communication with the sensor over UART and supports various configuration commands.

## Features

- Change sensor address
- Change baud rate
- Set upload mode (manual/automatic)
- Set upload interval
- Set LED mode
- Set relay mode
- Set communication mode (UART/Relay)
- Read distance
- Restore factory settings (soft/hard reset)

## Installation

To install the library, copy `XKC_KL200.py` to your MicroPython device.

## Usage

```python
import XKC_KL200
from machine import UART

# Initialize the sensor
sensor = XKC_KL200.XKC_KL200(uart_id=1, baudrate=9600)
sensor.begin(9600)

# Restore factory settings (hard reset)
sensor.restore_factory_settings(hard_reset=True)

# Change the sensor address
sensor.change_address(0x01)

# Change the baud rate
sensor.change_baud_rate(5)

# Set upload mode to automatic
sensor.set_upload_mode(auto_upload=True)

# Set upload interval to 50
sensor.set_upload_interval(50)

# Set LED mode
sensor.set_led_mode(1)

# Set relay mode
sensor.set_relay_mode(0)

# Set communication mode to UART
sensor.set_communication_mode(0)

# Read distance
distance = sensor.read_distance()
print("Distance:", distance)


Functions
begin(baudrate)

Initializes the UART interface with the given baudrate.
restore_factory_settings(hard_reset=True)

Restores the factory settings. If hard_reset is True, performs a hard reset (0xFE); otherwise, performs a soft reset (0xFD).
change_address(address)

Changes the sensor address. The address should be a 16-bit value.
change_baud_rate(baud_rate)

Changes the baud rate. The baud rate should be between 0 and 9.
set_upload_mode(auto_upload)

Sets the upload mode. If auto_upload is True, sets the mode to automatic; otherwise, sets it to manual.
set_upload_interval(interval)

Sets the upload interval. The interval should be between 1 and 100.
set_led_mode(mode)

Sets the LED mode. The mode should be between 0 and 3.
set_relay_mode(mode)

Sets the relay mode. The mode should be either 0 or 1.
set_communication_mode(mode)

Sets the communication mode. The mode should be either 0 (UART) or 1 (Relay).
read_distance()

Reads the distance from the sensor.
available()

Returns True if a new distance value is available.
get_distance()

Returns the last distance value and resets the availability status.
get_last_received_distance()

Returns the last received distance value.
