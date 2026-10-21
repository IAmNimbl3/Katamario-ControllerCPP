#include <Arduino.h>
#include <Wire.h>
#include <MPU6050.h>
#include "BallMotion.h"
#include "ControllerConfig.h"
#include "ControllerTransport.h"

ControllerTransport transport;

// Preliminary bench pin selection; confirm the breakout before wiring.
constexpr int SDA_PIN=21, SCL_PIN=22;
constexpr uint32_t SAMPLE_US=10000, OUTPUT_MS=20;
// Temporary alignment bypass. Disable when Unity supplies confirmation.
constexpr bool BYPASS_ALIGNMENT=true;
bool alineadoEnUnity=false; // Command a confirms only while awaiting alignment.
uint8_t address=0x68;
ball::Motion motion;
ball::Vec bias, sum;
ball::Output output;
enum class Mode { Waiting, AwaitingAlignment, Calibrating, Ready, Demo };
Mode mode=Mode::Waiting;
uint16_t calibrationCount=0;
uint32_t lastSample=0, lastOutput=0, lastProbe=0, demoStart=0;
bool calibrationDiagnostics=false;
bool movementDiagnostics=false;
uint32_t movementDiagnosticLast=0;
uint32_t diagnosticLastOutput=0;
uint32_t diagnosticSamples=0, diagnosticRejects[5]={};
uint16_t diagnosticBest=0;

// Observes every calibration sample; emits USB-only summaries twice per second.
// Off by default. No calibration thresholds or sensor settings are changed.
void recordCalibrationDiagnostic(ball::Vec accel, ball::Vec gyro, uint32_t elapsed) {
  if (!calibrationDiagnostics) return;
  const bool rejected[]={gyro.norm()>0.08f, std::abs(accel.x)>0.10f,
    std::abs(accel.y)>0.10f, std::abs(accel.z-1)>0.10f,
    elapsed>ball::config::MAX_SAMPLE_GAP_US};
  unsigned mask=0;
  for(unsigned i=0;i<5;i++) if(rejected[i]) { mask|=1u<<i; ++diagnosticRejects[i]; }
  ++diagnosticSamples;
  if(calibrationCount>diagnosticBest) diagnosticBest=calibrationCount;
  if(millis()-diagnosticLastOutput<500) return;
  diagnosticLastOutput=millis();
  Serial.printf("# CALRAW,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%lu,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu\n",
    accel.x,accel.y,accel.z,gyro.x,gyro.y,gyro.z,
    static_cast<unsigned long>(elapsed),mask,calibrationCount,diagnosticBest,
    static_cast<unsigned long>(diagnosticSamples),
    static_cast<unsigned long>(diagnosticRejects[0]),static_cast<unsigned long>(diagnosticRejects[1]),
    static_cast<unsigned long>(diagnosticRejects[2]),static_cast<unsigned long>(diagnosticRejects[3]),
    static_cast<unsigned long>(diagnosticRejects[4]));
  diagnosticSamples=0;
  for(auto &n:diagnosticRejects) n=0;
}

bool readSample(ball::Vec &accel, ball::Vec &gyro) {
  uint8_t data[14];
  // getMotion6 returns void; a checked burst rejects failed/partial I2C reads.
  if (I2Cdev::readBytes(address, MPU6050_RA_ACCEL_XOUT_H, 14, data, 20)!=14) return false;
  // word(...) is an Arduino macro; use a distinct name to decode the buffer.
  auto decodeInt16=[&](int i) { return static_cast<int16_t>((uint16_t(data[i])<<8)|data[i+1]); };
  accel=ball::Vec(decodeInt16(0),decodeInt16(2),decodeInt16(4))*(1.0f/16384.0f);
  gyro=ball::Vec(decodeInt16(8),decodeInt16(10),decodeInt16(12))*(ball::pi/(180.0f*16.4f));
  // Saturation loses orientation information; require a fresh calibration.
  return std::abs(int(decodeInt16(8)))<32700 && std::abs(int(decodeInt16(10)))<32700 &&
         std::abs(int(decodeInt16(12)))<32700;
}
void calibrate() {
  alineadoEnUnity=false; // Consume confirmation; do not reuse it after a fault.
  mode=Mode::Calibrating; calibrationCount=0; sum={}; output={}; motion.reset();
  transport.send("# CALIBRATING: 3 s quieta, ejes del sensor X derecha, Y adelante, Z arriba\n");
}
void waitForSensor(const char *reason) {
  alineadoEnUnity=false;
  mode=Mode::Waiting; output={}; motion.reset(); lastProbe=millis();
  char line[192]; snprintf(line,sizeof(line),"# WAITING: %s\n",reason);
  transport.send(line);
}
bool connectSensor() {
  const uint8_t addresses[]={0x68,0x69};
  for (uint8_t a : addresses) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission()!=0) continue;
    address=a;
    MPU6050 imu(a);
    if (!imu.testConnection()) continue;
    imu.initialize();
    imu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);
    imu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
    imu.setDLPFMode(MPU6050_DLPF_BW_42);
    imu.setRate(9); // DLPF enabled: 1 kHz / (1+9) = 100 Hz
    if (imu.getFullScaleGyroRange()!=MPU6050_GYRO_FS_2000 ||
        imu.getFullScaleAccelRange()!=MPU6050_ACCEL_FS_2 ||
        imu.getRate()!=9 || imu.getDLPFMode()!=MPU6050_DLPF_BW_42 || imu.getSleepEnabled()) continue;
    // A new connection/recenter request requires a fresh confirmation.
    alineadoEnUnity=false;
    mode=Mode::AwaitingAlignment; output={}; motion.reset();
    transport.send("# AWAITING_ALIGNMENT: esperando confirmacion o BYPASS_ALIGNMENT\n");
    return true;
  }
  return false;
}
const char *status() {
  switch(mode) {
    case Mode::Ready: return "ready";
    case Mode::Calibrating: return "calibrating";
    case Mode::AwaitingAlignment: return "awaiting_alignment";
    case Mode::Demo: return "demo";
    default: return "waiting";
  }
}
void setup() {
  Serial.begin(115200);
  Serial.println(transport.begin() ? "# BT_READY: Kyuboru SPP" : "# BT_ERROR: USB sigue disponible");
  Wire.begin(SDA_PIN,SCL_PIN); Wire.setClock(100000); Wire.setTimeOut(20);
  transport.send("# Kyuboru v1. Comandos: d demo, c reconectar, a confirmar alineacion, h ayuda\n");
  Serial.println("# CSV: K2,millis,status,right,forward,qw,qx,qy,qz");
  if (!connectSensor()) waitForSensor("MPU6050 ausente; salida cero. d inicia demo sin sensor");
  lastSample=micros();
}
// Single-byte bench commands shared by USB and SPP. CR/LF are ignored.
// Unity integration is not implemented. c never confirms alignment.
void handleCommand(char c) {
    if (c=='d') {
      alineadoEnUnity=false;
      mode=Mode::Demo; demoStart=millis(); motion.reset(); output={};
      transport.send("# DEMO: datos sinteticos, NO lecturas de la pelota\n");
    } else if (c=='c') {
      if (!connectSensor()) waitForSensor("sensor ausente");
      lastSample=micros();
    } else if (c=='h') {
      transport.send("# d: demo; c: reconectar; a: confirmar alineacion pendiente; r: diagnostico calibracion USB; h: ayuda\n");
    } else if (c=='m') {
      movementDiagnostics=!movementDiagnostics;
      Serial.println(movementDiagnostics ? "# MOTION_ON: ms,raw_gx,raw_gy,raw_gz,body_gx,body_gy,body_gz,world_gx,world_gy,world_gz,right,forward (gyro rad/s)" : "# MOTION_OFF");
    } else if (c=='r') {
      calibrationDiagnostics=!calibrationDiagnostics;
      diagnosticSamples=0; diagnosticBest=0; diagnosticLastOutput=millis();
      for(auto &n:diagnosticRejects) n=0;
      Serial.println(calibrationDiagnostics ? "# CALRAW_ON: ax_g,ay_g,az_g,gx_rad_s,gy_rad_s,gz_rad_s,dt_us,mask,good,best,n,reject_gyro,reject_x,reject_y,reject_z,reject_gap" : "# CALRAW_OFF");
    } else if (c=='a') {
      if (mode==Mode::AwaitingAlignment) {
        alineadoEnUnity=true;
        transport.send("# ACK: a\n");
      } else transport.send("# ERR: a requiere awaiting_alignment\n");
    } else if (c!='\r' && c!='\n' && c!=' ') {
      transport.send("# ERR: comando desconocido\n");
    }
}
void loop() {
  // Bound command handling to avoid starving the sampling loop.
  if (Serial.available()) handleCommand(Serial.read());
  int incoming=transport.readBluetooth();
  if (incoming>=0) handleCommand(static_cast<char>(incoming));
  if (mode==Mode::Waiting && millis()-lastProbe>=2000) {
    lastProbe=millis(); connectSensor(); lastSample=micros();
  }
  if (mode==Mode::AwaitingAlignment && (alineadoEnUnity || BYPASS_ALIGNMENT)) {
    calibrate();
    lastSample=micros();
  }
  uint32_t now=micros(), elapsed=now-lastSample;
  if (elapsed>=SAMPLE_US) {
    lastSample=now;
    float dt=elapsed*1e-6f;
    if (mode==Mode::Demo) {
      // Synthetic body-frame readings for fixed-frame scripted rotation.
      // 2 s each: stop, forward slow/fast, stop, right, back, left, twist.
      const ball::Vec phases[]={{0,0,0},{-0.8f,0,0},{-2.5f,0,0},{0,0,0},
                                {0,1.5f,0},{1.5f,0,0},{0,-1.5f,0},{0,0,1.5f}};
      auto inverse=motion.orientation.inverse();
      output=motion.update(inverse.rotate(phases[((millis()-demoStart)/2000)%8]),
                           inverse.rotate({0,0,1}),dt);
    } else if (mode==Mode::Ready || mode==Mode::Calibrating || mode==Mode::AwaitingAlignment) {
      ball::Vec accel, gyro;
      if (!readSample(accel,gyro)) waitForSensor("lectura fallida o giro saturado; recalibracion requerida");
      else if (mode==Mode::Calibrating) {
        recordCalibrationDiagnostic(accel,gyro,elapsed);
        // Gravity cannot determine forward: require a known starting pose.
        if (gyro.norm()>0.08f || std::abs(accel.x)>0.10f ||
            std::abs(accel.y)>0.10f || std::abs(accel.z-1)>0.10f ||
            elapsed>ball::config::MAX_SAMPLE_GAP_US) {
          calibrationCount=0; sum={};
        } else {
          sum=sum+gyro;
          if (++calibrationCount==300) {
            bias=sum*(1.0f/300); motion.reset(); mode=Mode::Ready;
            transport.send("# READY: calibracion terminada\n");
          }
        }
      } else if (elapsed>ball::config::MAX_SAMPLE_GAP_US)
        waitForSensor("seguimiento interrumpido: pausa de muestreo local");
      // Before alignment this is a provisional orientation, not a known heading.
      else {
        const auto body=gyro-bias;
        output=motion.update(body,accel,dt,mode==Mode::Ready);
        // Bench-only USB trace, same sample and orientation used for movement.
        // 10 Hz keeps diagnostic traffic below the serial link capacity.
        if (movementDiagnostics && mode==Mode::Ready && millis()-movementDiagnosticLast>=100) {
          movementDiagnosticLast=millis();
          const auto world=motion.orientation.rotate(body);
          Serial.printf("# MOTION,%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",
            static_cast<unsigned long>(movementDiagnosticLast),gyro.x,gyro.y,gyro.z,
            body.x,body.y,body.z,world.x,world.y,world.z,output.right,output.forward);
        }
      }
    }
  }
  if (millis()-lastOutput>=OUTPUT_MS) {
    lastOutput=millis();
    const ball::Quat &q=motion.orientation;
    char line[192];
    snprintf(line,sizeof(line),"K2,%lu,%s,%.4f,%.4f,%.6f,%.6f,%.6f,%.6f\n",
                  static_cast<unsigned long>(lastOutput),status(),output.right,output.forward,
                  q.w,q.x,q.y,q.z);
    transport.send(line,true);
  }
  delay(1);
}
