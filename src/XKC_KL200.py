import machine
import time

class XKC_KL200:
    def __init__(self, uart_id, baudrate=9600):
        self.uart = machine.UART(uart_id, baudrate)
        self.available = False
        self.distance = 0
        self.last_received_distance = 0

    def send_command(self, command):
        checksum = self.calculate_checksum(command)
        command.append(checksum)
        self.uart.write(bytearray(command))

    def calculate_checksum(self, data):
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def begin(self, baudrate):
        self.uart.init(baudrate)

    def restore_factory_settings(self, hard_reset=True):
        reset_byte = 0xFE if hard_reset else 0xFD
        command = [0x62, 0x39, 0x09, 0xFF, 0xFF, 0xFF, 0xFF, reset_byte]
        self.send_command(command)

    def change_address(self, address):
        if address > 0xFFFE:
            raise ValueError("Address out of range")
        command = [0x62, 0x32, 0x09, 0xFF, 0xFF, (address >> 8) & 0xFF, address & 0xFF]
        self.send_command(command)

    def change_baud_rate(self, baud_rate):
        if baud_rate > 9:
            raise ValueError("Baud rate out of range")
        command = [0x62, 0x30, 0x09, 0xFF, 0xFF, baud_rate]
        self.send_command(command)

    def set_upload_mode(self, auto_upload):
        mode = 1 if auto_upload else 0
        command = [0x62, 0x34, 0x09, 0xFF, 0xFF, mode]
        self.send_command(command)

    def set_upload_interval(self, interval):
        if interval < 1 or interval > 100:
            raise ValueError("Interval out of range")
        command = [0x62, 0x35, 0x09, 0xFF, 0xFF, interval]
        self.send_command(command)

    def set_led_mode(self, mode):
        if mode > 3:
            raise ValueError("LED mode out of range")
        command = [0x62, 0x37, 0x09, 0xFF, 0xFF, mode]
        self.send_command(command)

    def set_relay_mode(self, mode):
        if mode > 1:
            raise ValueError("Relay mode out of range")
        command = [0x62, 0x38, 0x09, 0xFF, 0xFF, mode]
        self.send_command(command)

    def set_communication_mode(self, mode):
        if mode > 1:
            raise ValueError("Communication mode out of range")
        command = [0x62, 0x31, 0x09, 0xFF, 0xFF, mode]
        self.send_command(command)

    def read_distance(self):
        command = [0x62, 0x33, 0x09, 0xFF, 0xFF, 0x00, 0x00, 0x00]
        self.send_command(command)

        # Wait for the response
        while self.uart.any() < 9:
            time.sleep(0.01)
        
        response = self.uart.read(9)
        if response[0] == 0x62 and response[1] == 0x33:
            length = response[2]
            address = (response[3] << 8) | response[4]
            raw_distance = (response[5] << 8) | response[6]
            checksum = response[8]
            calc_checksum = self.calculate_checksum(response[:8])

            if checksum == calc_checksum:
                self.distance = raw_distance
                self.last_received_distance = raw_distance
                self.available = True
        return self.distance

    def available(self):
        return self.available

    def get_distance(self):
        self.available = False
        return self.distance

    def get_last_received_distance(self):
        return self.last_received_distance
