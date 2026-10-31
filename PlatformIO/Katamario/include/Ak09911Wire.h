#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "Ak09911.h"

namespace ball {
class Ak09911Wire : public MagnetometerBus {
 public:
  explicit Ak09911Wire(TwoWire &wire) : wire_(wire) {}
  bool read(uint8_t address,uint8_t reg,uint8_t *data,uint8_t size) override {
    wire_.beginTransmission(address);
    wire_.write(reg);
    if (wire_.endTransmission(false)!=0) return false;
    if (wire_.requestFrom(address,static_cast<size_t>(size),true)!=size) {
      while (wire_.available()) wire_.read();
      return false;
    }
    for(uint8_t i=0;i<size;++i) data[i]=wire_.read();
    return true;
  }
  bool write(uint8_t address,uint8_t reg,uint8_t value) override {
    wire_.beginTransmission(address); wire_.write(reg); wire_.write(value);
    return wire_.endTransmission()==0;
  }
  void waitMicros(uint32_t us) override { delayMicroseconds(us); }
 private:
  TwoWire &wire_;
};
} // namespace ball
