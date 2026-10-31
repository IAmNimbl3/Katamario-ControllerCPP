#pragma once
#include "BallOrientation.h"

namespace ball { namespace magneticConfig {
// Opt in only after checking the actual MCU9911 board. False means zero extra
// I2C traffic and the existing MPU6050-only behavior, even without a magnetometer.
constexpr bool ENABLED=false;
inline BallOrientation::Settings settings() {
  BallOrientation::Settings result;
  result.enabled=ENABLED;
  result.quietSecondsBeforeCorrection=2.5f;
  result.maxGyroRadPerSecond=0.15f;
  result.stableFieldAngleRad=3.0f*pi/180.0f;
  result.stableRelativeFieldChange=0.05f;
  return result;
}
inline MagneticCalibration calibration() {
  MagneticCalibration result;
  // Populate measured hard-iron bias, soft-iron matrix and mounting rotation
  // for the assembled ball, then set valid=true. Identity is NOT a calibration.
  result.valid=false;
  return result;
}
} }
