#pragma once
#include <cstdint>

namespace ball {
namespace config {
// Starting pose tolerates placement tilt; still requires three quiet seconds.
constexpr float CALIBRATION_MAX_TILT_DEG = 25.0f;
constexpr float CALIBRATION_MIN_ACCEL_G = 0.85f;
constexpr float CALIBRATION_MAX_ACCEL_G = 1.15f;
constexpr float CALIBRATION_MAX_GYRO_RAD_PER_SEC = 0.08f;
constexpr uint16_t CALIBRATION_SAMPLES = 300;
// First bench tuning for interaction: vertical twist in either direction.
constexpr float TWIST_TRIGGER_RAD_PER_SEC = 1.5f;
// Playtest parameter: continuous same-direction travel above the speed threshold.
constexpr float TWIST_MIN_ANGLE_DEG = 180.0f;
constexpr float TWIST_MIN_ANGLE_RAD =
    TWIST_MIN_ANGLE_DEG * (3.14159265358979323846f / 180.0f);
constexpr float TWIST_VERTICAL_DOMINANCE = 1.25f;
constexpr float TWIST_RELEASE_RAD_PER_SEC = 0.35f;
constexpr float TWIST_RELEASE_SECONDS = 0.20f;
constexpr float TWIST_COOLDOWN_SECONDS = 0.60f;
// Gravity-based tilt correction, gated near rest. Tune with the actual mounting.
constexpr float TILT_MAX_GYRO_RAD_PER_SEC = 0.15f;
constexpr float TILT_MIN_ACCEL_G = 0.9f;
constexpr float TILT_MAX_ACCEL_G = 1.1f;
constexpr float TILT_CORRECTION_GAIN_PER_SEC = 2.0f;

// Movement-output dead zone; orientation tracking still integrates small turns.
// Initial value: 2 degrees/s (~0.035 rad/s).
// TODO physical tests: tune for sensor noise and small movements of the housing.
constexpr float MOVEMENT_DEADZONE_DEG_PER_SEC = 2.0f;
constexpr float MOVEMENT_DEADZONE_RAD_PER_SEC =
    MOVEMENT_DEADZONE_DEG_PER_SEC * (3.14159265358979323846f / 180.0f);

// Maximum LOCAL sensor sampling gap, not a Bluetooth reception timeout.
// TODO hardware/Bluetooth tests: tune this if scheduling or transmission blocks
// sampling. Unity must handle its own independent timeout for incoming packets.
constexpr uint32_t MAX_SAMPLE_GAP_US = 50000;
constexpr float MAX_SAMPLE_GAP_SECONDS = MAX_SAMPLE_GAP_US * 1e-6f;
} // namespace config
} // namespace ball
