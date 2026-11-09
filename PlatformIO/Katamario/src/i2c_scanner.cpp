#include <Arduino.h>
#include <Wire.h>

// Bench-only weak pull-up on sensor RST. Never drive this pin as OUTPUT.
constexpr int MAG_RST_PIN = 25;
// Address-only probes: no register writes.
void setup() {
  Serial.begin(115200);
  pinMode(MAG_RST_PIN, INPUT_PULLUP);
  delay(100);
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
}

void loop() {
  static unsigned round=0;
  Serial.printf("# RST GPIO25 INPUT_PULLUP digital=%d (not a voltage measurement)\n", digitalRead(MAG_RST_PIN));
  Serial.printf("# SCAN %u SDA=21 SCL=22 clock=100000 idle_sda=%d idle_scl=%d\n",
                ++round,digitalRead(21),digitalRead(22));
  unsigned found=0, errors=0;
  for (uint8_t address=0x08; address<=0x77; ++address) {
    Wire.beginTransmission(address);
    const uint8_t result=Wire.endTransmission();
    if (result==0) {
      ++found;
      Serial.printf("ACK 0x%02X\n",address);
    } else if (result!=2) {
      ++errors;
      Serial.printf("ERROR 0x%02X code=%u\n",address,result);
    }
    delay(2);
  }
  Serial.printf("# END found=%u other_errors=%u\n",found,errors);
  delay(2000);
}
