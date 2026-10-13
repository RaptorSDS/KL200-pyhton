import serial
import time
from enum import Enum


class XKC_KL200_Error(Enum):
    """Fehlercodes für die XKC_KL200 Klasse"""
    SUCCESS = 0
    INVALID_PARAMETER = 1
    TIMEOUT = 2
    CHECKSUM_ERROR = 3
    RESPONSE_ERROR = 4


class XKC_KL200:
    """
    Klasse zur Steuerung des XKC-KL200-2M-UART Laser-Abstandssensors

    Protokoll (siehe XKC-Datenblatt, Kapitel 11 "letter of agreement"):
        Byte 1-2  Befehl (z.B. 0x62 0x33 = "b3")
        Byte 3    Länge des gesamten Frames inkl. Prüfsumme
        Byte 4-5  Adresse (0xFFFF = Broadcast)
        Byte 6-7  Daten (High, Low)
        Byte 8    Antwort (0x00 im Befehl, 0x66 = Erfolg in der Antwort)
        Byte 9    XOR8-Prüfsumme über Byte 1-8
    """

    # Frame-Konstanten
    HEADER = 0x62
    HEADER_LINE = 0x61          # "a"-Befehle (Line-Modus, Antwortgeschwindigkeit)
    HEADER_STRING = 0x64        # "d"-Befehle (Konfiguration als String)
    ACK_OK = 0x66
    BROADCAST = 0xFFFF
    FRAME_LEN = 9
    CONFIG_FRAME_LEN = 0x1D     # 29 Byte Antwort auf "Konfiguration lesen"

    # Befehlscodes (zweites Byte)
    CMD_BAUD_RATE = 0x30        # b0 (mit 0x61 als erstes Byte: a0 Line-Modus)
    CMD_READ_CONFIG = 0x31      # b1
    CMD_ADDRESS = 0x32          # b2 (mit 0x61 als erstes Byte: a2 Antwortgeschwindigkeit)
    CMD_DISTANCE = 0x33         # b3
    CMD_UPLOAD_MODE = 0x34      # b4
    CMD_UPLOAD_INTERVAL = 0x35  # b5
    CMD_LED_MODE = 0x37         # b7
    CMD_RELAY_MODE = 0x38       # b8
    CMD_RESTORE = 0x39          # b9

    # Index aus dem Datenblatt -> Baudrate
    BAUD_RATES = (2400, 4800, 9600, 14400, 19200, 38400, 56000, 57600, 115200, 128000)

    def __init__(self, port, baudrate=9600, timeout=1.0, address=BROADCAST):
        """
        Initialisiert den XKC-KL200 Sensor

        Args:
            port (str): Serieller Port (z.B. '/dev/ttyUSB0', 'COM3')
            baudrate (int): Baudrate für die serielle Kommunikation (Standard: 9600)
            timeout (float): Timeout für Antworten des Sensors in Sekunden (Standard: 1.0)
            address (int): Geräteadresse (0-65534) oder 0xFFFF für Broadcast (Standard)
        """
        self._serial = serial.Serial(port, baudrate, timeout=0)
        self._timeout = timeout
        self._address = address & 0xFFFF
        self._buffer = bytearray()
        self._checksum_failed = False
        self._available = False
        self._distance = 0
        self._last_received_distance = 0
        self._auto_mode = False
        time.sleep(0.1)  # Kurze Pause für die Initialisierung des Sensors

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """Schließt die serielle Verbindung"""
        if self._serial.is_open:
            self._serial.close()

    # ------------------------------------------------------------------
    # Konfiguration
    # ------------------------------------------------------------------

    def hard_reset(self):
        """
        Setzt den Sensor auf Werkseinstellungen zurück (Xingkechuang default, 0xFE)

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        return self._execute(self.CMD_RESTORE, 0xFFFF, answer=0xFE)

    def soft_reset(self):
        """
        Setzt den Sensor auf Benutzereinstellungen zurück (0xFD)

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        return self._execute(self.CMD_RESTORE, 0xFFFF, answer=0xFD)

    def change_address(self, address):
        """
        Ändert die Adresse des Sensors

        Args:
            address (int): Neue Adresse (0-65534)

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(address, 0, 0xFFFE):
            return XKC_KL200_Error.INVALID_PARAMETER

        result = self._execute(self.CMD_ADDRESS, address)
        # Wurde der Sensor gezielt adressiert, ab jetzt die neue Adresse verwenden
        if result == XKC_KL200_Error.SUCCESS and self._address != self.BROADCAST:
            self._address = address
        return result

    def change_baud_rate(self, baud_rate, apply=True):
        """
        Ändert die Baudrate des Sensors

        Args:
            baud_rate (int): Baudrate-Index (0-9, siehe Dokumentation)
                0=2400, 1=4800, 2=9600, 3=14400, 4=19200, 5=38400,
                6=56000, 7=57600, 8=115200, 9=128000
            apply (bool): Bei Erfolg auch die lokale serielle Schnittstelle umstellen

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(baud_rate, 0, len(self.BAUD_RATES) - 1):
            return XKC_KL200_Error.INVALID_PARAMETER

        result = self._execute(self.CMD_BAUD_RATE, baud_rate)
        if result == XKC_KL200_Error.SUCCESS and apply:
            self._serial.baudrate = self.BAUD_RATES[baud_rate]
            self._buffer.clear()
        return result

    def set_upload_mode(self, auto_upload):
        """
        Setzt den Upload-Modus des Sensors

        Args:
            auto_upload (bool): True für automatischen Upload, False für manuellen Abfragemodus

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        result = self._execute(self.CMD_UPLOAD_MODE, 1 if auto_upload else 0)
        # Modus nur übernehmen, wenn der Sensor ihn bestätigt hat
        if result == XKC_KL200_Error.SUCCESS:
            self._auto_mode = bool(auto_upload)
        return result

    def set_upload_interval(self, interval):
        """
        Setzt das Upload-Intervall im automatischen Modus

        Args:
            interval (int): Intervall (1-100, entspricht 100ms-10s, Schrittweite 100ms)

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(interval, 1, 100):
            return XKC_KL200_Error.INVALID_PARAMETER
        return self._execute(self.CMD_UPLOAD_INTERVAL, interval)

    def set_led_mode(self, mode):
        """
        Konfiguriert das Verhalten der LED

        Args:
            mode (int): 0=an bei Erkennung, 1=aus bei Erkennung, 2=immer aus, 3=immer an

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(mode, 0, 3):
            return XKC_KL200_Error.INVALID_PARAMETER
        return self._execute(self.CMD_LED_MODE, mode)

    def set_relay_mode(self, mode):
        """
        Konfiguriert das Verhalten des Relais-Ausgangs (nur im Relais-Modus wirksam)

        Args:
            mode (int): 0=aktiv bei Erkennung, 1=inaktiv bei Erkennung

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(mode, 0, 1):
            return XKC_KL200_Error.INVALID_PARAMETER
        return self._execute(self.CMD_RELAY_MODE, mode)

    def set_communication_mode(self, mode):
        """
        Setzt den Kommunikationsmodus (Line-Modus) des Sensors

        Args:
            mode (int): 0=Relais-Modus, 1=UART-Modus

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(mode, 0, 1):
            return XKC_KL200_Error.INVALID_PARAMETER
        # Befehl a0 (0x61 0x30), der Sensor antwortet laut Datenblatt mit 0x62 0x30
        return self._execute(self.CMD_BAUD_RATE, mode, header=self.HEADER_LINE)

    def set_response_speed(self, mode):
        """
        Setzt die Antwortgeschwindigkeit (Trailing-Modus) des Sensors

        Args:
            mode (int): 0=hohe Präzision, 1=normal, 2=hohe Stabilität

        Returns:
            XKC_KL200_Error: SUCCESS bei Erfolg, sonst Fehlercode
        """
        if not self._in_range(mode, 0, 2):
            return XKC_KL200_Error.INVALID_PARAMETER
        # Befehl a2 (0x61 0x32), der Sensor antwortet laut Datenblatt mit 0x62 0x32
        return self._execute(self.CMD_ADDRESS, mode, header=self.HEADER_LINE)

    def read_config(self):
        """
        Liest die aktuelle Konfiguration des Sensors (Befehl b1)

        Returns:
            dict: Konfiguration oder None bei Timeout/Fehler
        """
        self._send_command(self.CMD_READ_CONFIG, 0)
        frame = self._wait_for_frame(self.CMD_READ_CONFIG)
        if frame is None or len(frame) != self.CONFIG_FRAME_LEN or frame[27] != self.ACK_OK:
            return None

        baud_index = frame[11]
        return {
            'calibrated': frame[10] != 0xFF,
            'baud_rate_index': baud_index,
            'baud_rate': self.BAUD_RATES[baud_index] if baud_index < len(self.BAUD_RATES) else None,
            'address': (frame[12] << 8) | frame[13],
            'calibration_distance': (frame[14] << 8) | frame[15],
            'upload_mode': frame[16],
            'upload_interval': frame[17],
            'led_mode': frame[20],
            'relay_mode': frame[21],
            'communication_mode': frame[22],
        }

    # ------------------------------------------------------------------
    # Distanzmessung
    # ------------------------------------------------------------------

    def read_distance(self, timeout=None):
        """
        Liest die aktuelle Distanz vom Sensor

        Im manuellen Modus wird eine Messung angefordert. Im automatischen Modus
        werden die bereits empfangenen Daten verarbeitet und der neueste Wert geliefert.

        Args:
            timeout (float): Timeout in Sekunden (Standard: Timeout aus dem Konstruktor)

        Returns:
            int: Gemessene Distanz in mm oder None bei Timeout/Fehler
        """
        if self._auto_mode:
            self.process_auto_data()
            return self._last_received_distance

        self._send_command(self.CMD_DISTANCE, 0)
        frame = self._wait_for_frame(self.CMD_DISTANCE, timeout)
        if frame is None:
            return None
        return self._distance

    def available(self):
        """
        Prüft, ob neue Distanzdaten verfügbar sind

        Returns:
            bool: True wenn neue Daten verfügbar sind, sonst False
        """
        if self._auto_mode:
            self.process_auto_data()
        return self._available

    def process_auto_data(self):
        """
        Verarbeitet alle eingehenden Daten im automatischen Modus

        Returns:
            bool: True wenn mindestens ein neuer Distanzwert verarbeitet wurde, sonst False
        """
        received = False
        while True:
            frame = self._poll_frame()
            if frame is None:
                return received
            if frame[1] == self.CMD_DISTANCE:
                received = True

    def get_distance(self):
        """
        Gibt die zuletzt gemessene Distanz zurück und setzt available() zurück

        Returns:
            int: Zuletzt gemessene Distanz in mm
        """
        self._available = False
        return self._distance

    def get_last_received_distance(self):
        """
        Gibt die zuletzt empfangene Distanz zurück (ohne _available zurückzusetzen)

        Returns:
            int: Zuletzt empfangene Distanz in mm
        """
        return self._last_received_distance

    # ------------------------------------------------------------------
    # Interne Hilfsfunktionen
    # ------------------------------------------------------------------

    @staticmethod
    def _in_range(value, low, high):
        return isinstance(value, int) and low <= value <= high

    def _execute(self, command, data, answer=0x00, header=HEADER):
        """Sendet einen Konfigurationsbefehl und wartet auf die Bestätigung"""
        self._send_command(command, data, answer, header)
        return self._wait_for_response(command)

    def _build_command(self, command, data, answer=0x00, header=HEADER):
        """
        Baut einen 9-Byte-Befehlsframe inkl. XOR8-Prüfsumme

        Returns:
            bytearray: Fertiger Befehlsframe
        """
        frame = bytearray([
            header, command, self.FRAME_LEN,
            (self._address >> 8) & 0xFF, self._address & 0xFF,
            (data >> 8) & 0xFF, data & 0xFF,
            answer, 0x00,
        ])
        frame[8] = self._calculate_checksum(frame[:8])
        return frame

    def _send_command(self, command, data, answer=0x00, header=HEADER):
        """
        Sendet einen Befehl an den Sensor

        Args:
            command (int): Befehlscode (zweites Byte)
            data (int): 16-Bit-Datenwert
            answer (int): Antwort-Byte (Byte 8), normalerweise 0x00
            header (int): Erstes Byte (0x62 oder 0x61)
        """
        if not self._auto_mode:
            # Alte Antworten verwerfen, damit sie nicht als Antwort auf diesen Befehl gelten
            self._serial.reset_input_buffer()
            self._buffer.clear()
        self._checksum_failed = False
        self._serial.write(self._build_command(command, data, answer, header))
        self._serial.flush()

    @staticmethod
    def _calculate_checksum(data):
        """
        Berechnet die XOR8-Prüfsumme

        Args:
            data (bytes or bytearray): Datenarray

        Returns:
            int: Berechnete Prüfsumme
        """
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def _poll_frame(self):
        """
        Liest verfügbare Bytes ohne zu blockieren und gibt den nächsten gültigen Frame zurück.
        Distanz-Frames werden dabei sofort ausgewertet.

        Returns:
            bytes: Gültiger Frame oder None, wenn (noch) keiner vollständig ist
        """
        waiting = self._serial.in_waiting
        if waiting:
            self._buffer.extend(self._serial.read(waiting))

        buf = self._buffer
        while True:
            # Auf Frame-Anfang synchronisieren
            start = buf.find(self.HEADER)
            if start < 0:
                buf.clear()
                return None
            if start:
                del buf[:start]
            if len(buf) < 3:
                return None

            length = buf[2]
            if length not in (self.FRAME_LEN, self.CONFIG_FRAME_LEN):
                del buf[0]  # Kein gültiger Header, ein Byte weiter suchen
                continue
            if len(buf) < length:
                return None

            frame = bytes(buf[:length])
            if self._calculate_checksum(frame[:-1]) != frame[-1]:
                self._checksum_failed = True
                del buf[0]
                continue

            del buf[:length]
            if frame[1] == self.CMD_DISTANCE and length == self.FRAME_LEN:
                distance = (frame[5] << 8) | frame[6]
                self._distance = distance
                self._last_received_distance = distance
                self._available = True
            return frame

    def _wait_for_frame(self, command, timeout=None):
        """
        Wartet auf einen gültigen Antwortframe für den angegebenen Befehl.
        Dazwischen eintreffende Distanz-Frames (Auto-Modus) werden verarbeitet.

        Returns:
            bytes: Antwortframe oder None bei Timeout
        """
        deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
        while True:
            frame = self._poll_frame()
            if frame is not None:
                if frame[1] == command:
                    return frame
                continue
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.005)

    def _wait_for_response(self, command, timeout=None):
        """
        Wartet auf die Bestätigung (ACK) eines Konfigurationsbefehls

        Args:
            command (int): Erwarteter Befehlscode in der Antwort
            timeout (float): Timeout in Sekunden (Standard: Timeout aus dem Konstruktor)

        Returns:
            XKC_KL200_Error: SUCCESS, TIMEOUT, CHECKSUM_ERROR oder RESPONSE_ERROR
        """
        frame = self._wait_for_frame(command, timeout)
        if frame is None:
            if self._checksum_failed:
                return XKC_KL200_Error.CHECKSUM_ERROR
            return XKC_KL200_Error.TIMEOUT
        if frame[7] != self.ACK_OK:
            return XKC_KL200_Error.RESPONSE_ERROR
        return XKC_KL200_Error.SUCCESS
