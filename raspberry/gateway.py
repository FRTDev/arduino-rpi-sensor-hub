#!/usr/bin/env python3
"""Passerelle Raspberry Pi -> Arduinos -> Serveur Flask."""

from datetime import datetime
import os
import time

import requests
import serial
import RPi.GPIO as GPIO

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000").rstrip("/")
SERIAL_ARD1 = "/dev/ttyUSB0"
SERIAL_ARD2 = "/dev/ttyUSB1"
BUTTON_PIN = 4
PERIOD_SECONDS = 120
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "gateway2026")


class RaspberryGateway:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.ser1 = serial.Serial(SERIAL_ARD1, 9600, timeout=1)
        self.ser2 = serial.Serial(SERIAL_ARD2, 9600, timeout=1)
        time.sleep(2)
        self._auto_detect_ports()

    def _identify_arduino(self, serial_port):
        try:
            serial_port.reset_input_buffer()
            serial_port.write(b"GET\n")
            for _ in range(3):
                line = serial_port.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("ARD1:VAL:"):
                    return "arduino1"
                if line.startswith("ARD2:TEMP:"):
                    return "arduino2"
        except Exception as e:
            print(f"[ERREUR] Detection port serie: {e}")
        return None

    def _auto_detect_ports(self):
        id_usb0 = self._identify_arduino(self.ser1)
        id_usb1 = self._identify_arduino(self.ser2)

        print(f"[SERIE] {SERIAL_ARD1} -> {id_usb0 or 'inconnu'}")
        print(f"[SERIE] {SERIAL_ARD2} -> {id_usb1 or 'inconnu'}")

        if id_usb0 == "arduino2" and id_usb1 == "arduino1":
            self.ser1, self.ser2 = self.ser2, self.ser1
            print("[SERIE] Ports inverses detectes, remappage applique")

    def lire_arduino(self, serial_port, arduino_id):
        try:
            serial_port.reset_input_buffer()
            serial_port.write(b"GET\n")
            for _ in range(3):
                reponse = serial_port.readline().decode("utf-8", errors="ignore").strip()
                if not reponse:
                    continue
                if arduino_id == "arduino1" and reponse.startswith("ARD1:VAL:"):
                    return reponse.split(":")[-1]
                if arduino_id == "arduino2" and reponse.startswith("ARD2:TEMP:"):
                    return reponse.split(":")[-1]
                print(f"[SERIE] Reponse inattendue {arduino_id}: '{reponse}'")
        except Exception as e:
            print(f"[ERREUR] Lecture {arduino_id}: {e}")
        return None

    def envoyer_serveur(self, arduino_id, valeur):
        try:
            payload = {
                "arduino_id": arduino_id,
                "valeur": str(valeur),
                "timestamp": datetime.now().isoformat(),
            }
            headers = {"X-API-Key": GATEWAY_API_KEY}
            r = requests.post(f"{SERVER_URL}/api/data", json=payload, headers=headers, timeout=5)
            if 200 <= r.status_code < 300:
                print(f"[OK] {arduino_id}: {valeur} -> serveur ({r.status_code})")
            else:
                body = r.text.strip().replace("\n", " ")
                print(
                    f"[ERREUR] POST /api/data {arduino_id}={valeur} "
                    f"status={r.status_code} body={body}"
                )
        except requests.exceptions.ConnectionError:
            print(f"[ERREUR] Serveur inaccessible sur {SERVER_URL} (POST /api/data)")
        except Exception as e:
            print(f"[ERREUR] Envoi serveur: {e}")

    def recuperer_consignes(self):
        try:
            headers = {"X-API-Key": GATEWAY_API_KEY}
            r = requests.get(f"{SERVER_URL}/api/consignes", headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json()
        except requests.exceptions.ConnectionError:
            print(f"[ERREUR] Serveur inaccessible sur {SERVER_URL} (GET /api/consignes)")
        except Exception as e:
            print(f"[ERREUR] Lecture consignes: {e}")
        return {}

    def envoyer_consigne(self, serial_port, commande):
        try:
            cmd = f"{str(commande).strip().upper()}\n"
            serial_port.write(cmd.encode("utf-8"))
            ack = serial_port.readline().decode("utf-8", errors="ignore").strip()
            print(f"[CONSIGNE] {cmd.strip()} | reponse: {ack}")
        except Exception as e:
            print(f"[ERREUR] Envoi consigne: {e}")

    def cycle_lecture(self):
        val1 = self.lire_arduino(self.ser1, "arduino1")
        if val1 is not None:
            self.envoyer_serveur("arduino1", val1)

        val2 = self.lire_arduino(self.ser2, "arduino2")
        if val2 is not None:
            self.envoyer_serveur("arduino2", val2)

        consignes = self.recuperer_consignes()
        if consignes.get("arduino1"):
            self.envoyer_consigne(self.ser1, consignes["arduino1"])
        if consignes.get("arduino2"):
            self.envoyer_consigne(self.ser2, consignes["arduino2"])

    def run(self):
        print("[GATEWAY] Demarrage (bouton GPIO4 + envoi toutes les 2 minutes)")
        print(f"[GATEWAY] Serveur cible: {SERVER_URL}")
        next_period = time.time()
        try:
            while True:
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    print("[GPIO] Bouton presse -> lecture immediate")
                    self.cycle_lecture()
                    time.sleep(0.3)

                now = time.time()
                if now >= next_period:
                    print("[TIMER] Cycle periodique")
                    self.cycle_lecture()
                    next_period = now + PERIOD_SECONDS

                time.sleep(0.1)
        finally:
            GPIO.cleanup()
            self.ser1.close()
            self.ser2.close()


if __name__ == "__main__":
    RaspberryGateway().run()
