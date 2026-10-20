// Bench-only observation of the production calibration conditions.
#include <Arduino.h>
#include <Wire.h>
#include <MPU6050.h>
#include <cmath>
#include "ControllerConfig.h"

uint8_t diagnosticAddress=0x68;
uint32_t diagnosticLast=0;
unsigned diagnosticSequence=0, diagnosticGood=0, diagnosticBest=0;
bool diagnosticConnected=false;

void setup() {
  Serial.begin(115200);
  Wire.begin(21,22); Wire.setClock(100000); Wire.setTimeOut(20);
  for (uint8_t addr : {uint8_t(0x68),uint8_t(0x69)}) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission()!=0) continue;
    MPU6050 imu(addr);
    Serial.printf("# PROBE address=0x%02X whoami=0x%02X connection=%d\n",addr,imu.getDeviceID(),imu.testConnection());
    if (!imu.testConnection()) continue;
    diagnosticAddress=addr;
    imu.initialize();
    imu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);
    imu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
    imu.setDLPFMode(MPU6050_DLPF_BW_42); imu.setRate(9);
    Serial.printf("# CONFIG gyro=%u accel=%u dlpf=%u rate=%u sleep=%d\n",imu.getFullScaleGyroRange(),imu.getFullScaleAccelRange(),imu.getDLPFMode(),imu.getRate(),imu.getSleepEnabled());
    diagnosticConnected=true; break;
  }
  if (diagnosticConnected) {
    for (uint8_t reg : {uint8_t(0x75),uint8_t(0x6B),uint8_t(0x6C),uint8_t(0x1B),uint8_t(0x1C)}) {
      Wire.beginTransmission(diagnosticAddress); Wire.write(reg);
      int err=Wire.endTransmission(false);
      int n=Wire.requestFrom(diagnosticAddress,uint8_t(1));
      Serial.printf("# REG %02X err=%d n=%d value=%02X\n",reg,err,n,Wire.read());
    }
  }
  Serial.println("# RAW,us,ax_raw,ay_raw,az_raw,gx_raw,gy_raw,gz_raw,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,gyro_rad_s,flags,good,best");
  // flags: 1 gyro>0.08rad/s; 2 |ax|>0.1g; 4 |ay|>0.1g;
  // 8 |az-1|>0.1g; 16 sample gap>50ms; 32 saturated; 64 I2C read failed.
  diagnosticLast=micros();
}
void loop() {
  if (!diagnosticConnected) { Serial.println("# NO_SENSOR"); delay(1000); return; }
  uint32_t now=micros(), gap=now-diagnosticLast;
  if (gap<10000) { delay(1); return; }
  diagnosticLast=now;
  uint8_t data[14]={};
  int received=I2Cdev::readBytes(diagnosticAddress,MPU6050_RA_ACCEL_XOUT_H,14,data,20);
  if (diagnosticSequence%100==0) {
    Serial.print("# LIB_BYTES");
    for (uint8_t b : data) Serial.printf(" %02X",b);
    Serial.println();
    Wire.beginTransmission(diagnosticAddress); Wire.write(uint8_t(0x3B));
    int err=Wire.endTransmission(false);
    int n=Wire.requestFrom(diagnosticAddress,uint8_t(14));
    Serial.printf("# DIRECT err=%d n=%d bytes",err,n);
    while(Wire.available()) Serial.printf(" %02X",Wire.read());
    Serial.println();
    Serial.print("# SINGLE");
    for (uint8_t reg=0x3B;reg<=0x48;reg++) {
      Wire.beginTransmission(diagnosticAddress); Wire.write(reg); Wire.endTransmission(false);
      Wire.requestFrom(diagnosticAddress,uint8_t(1));
      Serial.printf(" %02X",Wire.read());
    }
    Serial.println();
  }
  // Arduino.h defines word(...) as a macro; avoid that name for decoding.
  auto decodeInt16=[&](int i){ return static_cast<int16_t>((uint16_t(data[i])<<8)|data[i+1]); };
  int ax=decodeInt16(0), ay=decodeInt16(2), az=decodeInt16(4), gx=decodeInt16(8), gy=decodeInt16(10), gz=decodeInt16(12);
  float x=ax/16384.f,y=ay/16384.f,z=az/16384.f;
  float dx=gx/16.4f,dy=gy/16.4f,dz=gz/16.4f;
  float norm=std::sqrt(dx*dx+dy*dy+dz*dz)*3.14159265358979323846f/180.f;
  unsigned flags=(norm>0.08f?1:0) | (std::abs(x)>0.1f?2:0) | (std::abs(y)>0.1f?4:0) |
    (std::abs(z-1)>0.1f?8:0) | (gap>ball::config::MAX_SAMPLE_GAP_US?16:0) |
    (std::abs(gx)>=32700 || std::abs(gy)>=32700 || std::abs(gz)>=32700?32:0) | (received!=14?64:0);
  diagnosticGood=flags?0:diagnosticGood+1;
  if (diagnosticGood>diagnosticBest) diagnosticBest=diagnosticGood;
  if (++diagnosticSequence%10==0)
    Serial.printf("RAW,%lu,%d,%d,%d,%d,%d,%d,%.6f,%.6f,%.6f,%.5f,%.5f,%.5f,%.6f,%u,%u,%u\n",
      static_cast<unsigned long>(gap),ax,ay,az,gx,gy,gz,x,y,z,dx,dy,dz,norm,flags,diagnosticGood,diagnosticBest);
}
