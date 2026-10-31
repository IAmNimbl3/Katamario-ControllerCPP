#pragma once
#include <cstdint>
#include <initializer_list>
#include "BallMotion.h"

namespace ball {
// Small portable bus contract: the driver does not own Wire or MPU6050 settings.
struct MagnetometerBus {
  virtual ~MagnetometerBus() = default;
  virtual bool read(uint8_t address, uint8_t reg, uint8_t *data, uint8_t size)=0;
  virtual bool write(uint8_t address, uint8_t reg, uint8_t value)=0;
  virtual void waitMicros(uint32_t us)=0;
};

// AKM MS1526-E-01 (2014/7), sections 6, 7 and 8. Not an AK8963 driver.
class Ak09911 {
 public:
  enum class Result { Sample, NotReady, Overflow, IoError, Offline };
  explicit Ak09911(MagnetometerBus &bus) : bus_(bus) {}
  bool online() const { return online_; }
  uint8_t address() const { return address_; }

  // Call at setup or explicit reconnect, never during the timed sample update.
  bool begin() {
    online_=false;
    for (uint8_t address : {uint8_t(0x0c), uint8_t(0x0d)}) {
      address_=address;
      uint8_t id[2];
      if (!bus_.read(address_,0x00,id,2) || id[0]!=0x48 || id[1]!=0x05) continue;
      if (!bus_.write(address_,0x32,0x01)) continue; // Soft reset.
      bus_.waitMicros(1000);
      if (!setMode(0x1f)) continue; // Fuse ROM sensitivity adjustment.
      uint8_t asa[3];
      const bool read=bus_.read(address_,0x60,asa,3);
      if (!setMode(0x00) || !read) continue;
      // AK09911 uses (ASA / 128 + 1), NOT the AK8963 adjustment formula.
      for (int i=0;i<3;++i) scale_[i]=0.6f*(1.0f+asa[i]/128.0f);
      if (!setMode(0x08)) continue; // Continuous measurement, 100 Hz.
      uint8_t mode;
      if (!bus_.read(address_,0x31,&mode,1) || (mode&0x1f)!=0x08) continue;
      online_=true;
      return true;
    }
    return false;
  }

  // Output in microteslas in magnetometer axes. Unchanged on failure.
  Result read(Vec &field) {
    if (!online_) return Result::Offline;
    uint8_t status;
    if (!bus_.read(address_,0x10,&status,1)) return fail();
    if (!(status&1)) return Result::NotReady;
    // Burst includes TMPS and ST2: reading ST2 releases the protected sample.
    uint8_t bytes[8];
    if (!bus_.read(address_,0x11,bytes,8)) return fail();
    if (bytes[7]&0x08) return Result::Overflow;
    auto decode=[&](int i) {
      return static_cast<int16_t>(uint16_t(bytes[i]) | (uint16_t(bytes[i+1])<<8));
    };
    // ST1.DOR means an older sample was skipped, not that this sample is invalid.
    field={decode(0)*scale_[0],decode(2)*scale_[1],decode(4)*scale_[2]};
    return Result::Sample;
  }
 private:
  bool setMode(uint8_t mode) {
    if (!bus_.write(address_,0x31,0)) return false;
    bus_.waitMicros(100); // Twat, including transitions out of Fuse ROM.
    if (mode && !bus_.write(address_,0x31,mode)) return false;
    bus_.waitMicros(100);
    return true;
  }
  Result fail() { online_=false; return Result::IoError; }
  MagnetometerBus &bus_;
  uint8_t address_=0;
  float scale_[3]={};
  bool online_=false;
};
} // namespace ball
