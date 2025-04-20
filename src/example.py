
#!/usr/bin/env python3
import time
import logging
from xkc_kl200 import XKC_KL200, XKC_KL200_Error

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('XKC_KL200_Demo')

def main():
    # Sensor am seriellen Port anschließen (anpassen je nach System)
    PORT = '/dev/ttyUSB0'
    
    try:
        # Sensor initialisieren
        logger.info(f"Verbinde mit Sensor an Port {PORT}")
        sensor = XKC_KL200(PORT, baudrate=9600)
        
        # Konfiguration des Sensors
        logger.info("Konfiguriere Sensor...")
        
        # Kommunikationsmodus setzen
        result = sensor.set_communication_mode(1)  # UART-Modus
        if result != XKC_KL200_Error.SUCCESS:
            logger.error(f"Fehler beim Setzen des Kommunikationsmodus: {result}")
            return
        
        # Upload-Modus setzen (hier: manueller Modus)
        result = sensor.set_upload_mode(False)
        if result != XKC_KL200_Error.SUCCESS:
            logger.error(f"Fehler beim Setzen des Upload-Modus: {result}")
            return
        
        # LED-Modus setzen
        result = sensor.set_led_mode(0)  # LED leuchtet bei Erkennung
        if result != XKC_KL200_Error.SUCCESS:
            logger.error(f"Fehler beim Setzen des LED-Modus: {result}")
            return
        
        logger.info("Sensor erfolgreich konfiguriert. Starte Messungen...")
        
        # Hauptschleife für Messungen
        try:
            while True:
                try:
                    # Distanz messen mit Timeout
                    distance = sensor.read_distance(timeout=0.5)
                    
                    # Ergebnis ausgeben
                    logger.info(f"Gemessene Distanz: {distance} mm")
                    
                except Exception as e:
                    logger.error(f"Fehler bei der Messung: {e}")
                
                time.sleep(1.0)  # Alle 1 Sekunde messen
        
        except KeyboardInterrupt:
            logger.info("Messung durch Benutzer beendet.")
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
    
    finally:
        # Verbindung zum Sensor schließen
        if 'sensor' in locals():
            logger.info("Schließe Verbindung zum Sensor...")
            sensor.close()
            logger.info("Verbindung geschlossen.")

if __name__ == "__main__":
    main()
