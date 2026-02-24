/*
 * Arduino 2 - Capteur de temperature TMP36
 * Protocole:
 *   GET          -> "ARD2:TEMP:<valeur>"
 *   AUTO         -> couleur selon temperature
 *   OFF/RED/GREEN/BLUE -> couleur forcee
 */

const int TEMP_PIN = A0;
const int RED_PIN = 9;
const int GREEN_PIN = 10;
const int BLUE_PIN = 11;

String modeLed = "AUTO";

float lireTemperature() {
  int reading = analogRead(TEMP_PIN);
  float voltage = reading * 5.0 / 1024.0;
  return (voltage - 0.5) * 100.0;
}

void setColor(int r, int g, int b) {
  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

void appliquerLed(float temperature) {
  if (modeLed == "OFF") {
    setColor(0, 0, 0);
    return;
  }
  if (modeLed == "RED") {
    setColor(255, 0, 0);
    return;
  }
  if (modeLed == "GREEN") {
    setColor(0, 255, 0);
    return;
  }
  if (modeLed == "BLUE") {
    setColor(0, 0, 255);
    return;
  }

  if (temperature < 20.0) {
    setColor(0, 0, 255);
  } else if (temperature <= 25.0) {
    setColor(0, 255, 0);
  } else {
    setColor(255, 0, 0);
  }
}

void traiterCommande(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "GET") {
    float t = lireTemperature();
    Serial.print("ARD2:TEMP:");
    Serial.println(t, 1);
    return;
  }

  if (cmd == "AUTO" || cmd == "OFF" || cmd == "RED" || cmd == "GREEN" || cmd == "BLUE") {
    modeLed = cmd;
    appliquerLed(lireTemperature());
    Serial.println("ACK");
    return;
  }

  Serial.println("ERR");
}

void setup() {
  Serial.begin(9600);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  appliquerLed(lireTemperature());
}

void loop() {
  appliquerLed(lireTemperature());

  if (Serial.available()) {
    String commande = Serial.readStringUntil('\n');
    traiterCommande(commande);
  }

  delay(100);
}
