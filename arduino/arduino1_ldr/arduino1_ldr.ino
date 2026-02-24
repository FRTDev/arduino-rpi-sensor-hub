/*
 * Arduino 1 - Capteur de luminosite (LDR)
 * Protocole:
 *   GET  -> "ARD1:VAL:<valeur>"
 *   AUTO -> LED selon luminosite
 *   ON   -> allume la LED
 *   OFF  -> eteint la LED
 */

const int LDR_PIN = A0;
const int LED_PIN = 9;
const int SEUIL_LDR = 500;

bool ledAllumee = false;
bool modeAuto = true;

void appliquerLedAuto() {
  int valeur = analogRead(LDR_PIN);
  ledAllumee = (valeur < SEUIL_LDR);
}

void appliquerLed() {
  digitalWrite(LED_PIN, ledAllumee ? HIGH : LOW);
}

void traiterCommande(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "GET") {
    int valeur = analogRead(LDR_PIN);
    Serial.print("ARD1:VAL:");
    Serial.println(valeur);
    return;
  }

  if (cmd == "AUTO") {
    modeAuto = true;
    appliquerLedAuto();
    appliquerLed();
    Serial.println("ACK");
    return;
  }

  if (cmd == "ON") {
    modeAuto = false;
    ledAllumee = true;
    appliquerLed();
    Serial.println("ACK");
    return;
  }

  if (cmd == "OFF") {
    modeAuto = false;
    ledAllumee = false;
    appliquerLed();
    Serial.println("ACK");
    return;
  }

  Serial.println("ERR");
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  appliquerLedAuto();
  appliquerLed();
}

void loop() {
  if (modeAuto) {
    appliquerLedAuto();
    appliquerLed();
  }

  if (Serial.available()) {
    String commande = Serial.readStringUntil('\n');
    traiterCommande(commande);
  }
  delay(50);
}
