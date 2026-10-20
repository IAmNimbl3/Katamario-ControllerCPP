#pragma once
#include <cstdint>

namespace ball {
namespace config {
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
