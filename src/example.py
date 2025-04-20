#!/usr/bin/env python3
import time
from xkc_kl200 import XKC_KL200, XKC_KL200_Error

def main():
    # Sensor am seriellen Port anschließen (anpassen je nach System)
    # Unter Windows z.B. 'COM3', unter Linux z.B. '/dev/ttyUSB0'
    PORT = '/dev/ttyUSB0'
    
    try:
        # Sensor initialisieren
        sensor = XKC_KL200(PORT, baudrate=9600)
        print("XKC-KL200 Laser-Abstandssensor Test (Auto-Modus)")
        
        # Konfiguration des Sensors
        result = sensor.set_communication_mode(1)  # UART-Modus
        if result != XKC_KL200_Error.SUCCESS:
            print(f"Fehler beim Setzen des Kommunikationsmodus: {result}")
        
        result = sensor.set_upload_mode(True)  # Automatischer Upload-Modus
        if result != XKC_KL200_Error.SUCCESS:
            print(f"Fehler beim Setzen des Upload-Modus: {result}")
        
        result = sensor.set_upload_interval(5)  # Intervall: 500ms
        if result != XKC_KL200_Error.SUCCESS:
            print(f"Fehler beim Setzen des Upload-Intervalls: {result}")
        
        print("Sensor konfiguriert. Empfange automatische Messungen...")
        
        # Hauptschleife für automatische Messungen
        try:
            while True:
                # Prüfen, ob neue Daten verfügbar sind
                if sensor.available():
                    # Daten verarbeiten
                    if sensor.process_auto_data():
                        # Distanz auslesen und ausgeben
                        distance = sensor.get_distance()
                        print(f"Distanz: {distance} mm")
                
                # Kurze Pause, um CPU-Last zu reduzieren
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nMessung beendet.")
    
    except Exception as e:
        print(f"Fehler: {e}")
    
    finally:
        # Verbindung zum Sensor schließen
        if 'sensor' in locals():
            sensor.close()

if __name__ == "__main__":
    main()
