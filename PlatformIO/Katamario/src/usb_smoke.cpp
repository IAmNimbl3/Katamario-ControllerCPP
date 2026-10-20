#include <Arduino.h>

void setup() { Serial.begin(115200); }
void loop() {
  Serial.println("Katamario: ESP32 funcionando");
  delay(1000);
}
