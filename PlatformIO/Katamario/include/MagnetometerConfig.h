#pragma once
#include "BallOrientation.h"

namespace ball { namespace magneticConfig {
// Opt in only after checking the actual MCU9911 board. False means zero extra
// I2C traffic and the existing MPU6050-only behavior, even without a magnetometer.
constexpr bool ENABLED=true; // Provisional correction enabled; set calibration.valid=false to disable aiding.
// MCU9911 RST wired to GPIO25: weak bias only, never an actively driven output.
// Set -1 for boards that already hold RST high without this connection.
constexpr int RESET_PULLUP_PIN=25;
inline BallOrientation::Settings settings() {
  BallOrientation::Settings result;
  result.enabled=ENABLED;
  result.fieldSmoothingSeconds=0.2f; // Measured stationary noise ~0.9 uT/axis.
  result.quietSecondsBeforeCorrection=2.5f;
  result.maxGyroRadPerSecond=0.15f;
  result.stableFieldAngleRad=3.0f*pi/180.0f;
  result.stableRelativeFieldChange=0.05f;
  return result;
}
inline MagneticCalibration calibration() {
  MagneticCalibration result;
  // PROVISIONAL: fitted from capture-axes.log on 2026-11-10.
  // Joint affine fit against MPU orientations; polar decomposition separates
  // mounting rotation from soft-iron compensation. Not a precision calibration.
  // Unit-determinant soft-iron scale preserves the measured field scale.
  result.biasMicrotesla={-59.18909209f, 9.80047817f, -13.98450739f};
  result.matrixRows[0]={1.07860687f, -0.02714685f, 0.00327242f};
  result.matrixRows[1]={-0.02714685f, 0.93970999f, -0.01853453f};
  result.matrixRows[2]={0.00327242f, -0.01853453f, 0.98769462f};
  result.mounting={0.99414376f, 0.00143480f, 0.00399433f, 0.10798231f};
  result.valid=true;
  return result;
}
} }
