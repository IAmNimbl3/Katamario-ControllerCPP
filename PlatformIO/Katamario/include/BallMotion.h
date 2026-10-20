#pragma once
#include <cmath>
#include "ControllerConfig.h"

namespace ball {
constexpr float pi = 3.14159265358979323846f;
struct Vec {
  float x = 0, y = 0, z = 0;
  Vec() = default;
  Vec(float a, float b, float c) : x(a), y(b), z(c) {}
  Vec operator+(Vec b) const { return {x+b.x, y+b.y, z+b.z}; }
  Vec operator-(Vec b) const { return {x-b.x, y-b.y, z-b.z}; }
  Vec operator*(float s) const { return {x*s, y*s, z*s}; }
  float norm() const { return std::sqrt(x*x+y*y+z*z); }
};
inline Vec cross(Vec a, Vec b) {
  return {a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x};
}
struct Quat {
  float w=1, x=0, y=0, z=0;
  Quat() = default;
  Quat(float a, float b, float c, float d) : w(a),x(b),y(c),z(d) {}
  Quat operator*(Quat b) const {
    return {w*b.w-x*b.x-y*b.y-z*b.z, w*b.x+x*b.w+y*b.z-z*b.y,
            w*b.y-x*b.z+y*b.w+z*b.x, w*b.z+x*b.y-y*b.x+z*b.w};
  }
  Quat inverse() const { return {w,-x,-y,-z}; }
  void normalize() {
    float n=std::sqrt(w*w+x*x+y*y+z*z); w/=n; x/=n; y/=n; z/=n;
  }
  Vec rotate(Vec v) const {
    Quat r=(*this)*Quat(0,v.x,v.y,v.z)*inverse(); return {r.x,r.y,r.z};
  }
};
struct Output { float right=0, forward=0; };

// Calibration frame: X right, Y forward, Z up. Gyro rad/s; accel g.
class Motion {
 public:
  Quat orientation;
  float fullSpeed = pi;   // 180 degrees/s gives magnitude 1
  void reset() { orientation=Quat(); }

  // Placeholder: future action for rotation about the fixed vertical axis.
  // Input would be world.z (signed rad/s), NOT the sensor's local gyro.z.
  // Intentionally empty and not called anywhere; no gameplay effect yet.
  void onVerticalRotation(float verticalAngularVelocityRadPerSec) {
    (void)verticalAngularVelocityRadPerSec;
  }

  Output update(Vec gyro, Vec accel, float dt, bool movementEnabled=true) {
    if (!(dt>0 && dt<=config::MAX_SAMPLE_GAP_SECONDS)) return {};
    Vec corrected=gyro;
    const float an=accel.norm();
    // Correct tilt near rest only, reducing off-center acceleration effects.
    // Gravity does NOT observe absolute heading.
    if (gyro.norm()<config::TILT_MAX_GYRO_RAD_PER_SEC &&
        an>config::TILT_MIN_ACCEL_G && an<config::TILT_MAX_ACCEL_G) {
      Vec expected=orientation.inverse().rotate({0,0,1});
      corrected=corrected+cross(accel*(1/an),expected)*config::TILT_CORRECTION_GAIN_PER_SEC;
    }
    float speed=corrected.norm();
    if (speed>1e-8f) {
      float half=speed*dt*0.5f, s=std::sin(half)/speed;
      orientation=orientation*Quat(std::cos(half),corrected.x*s,corrected.y*s,corrected.z*s);
      orientation.normalize();
    }
    // Preview can track orientation without enabling gameplay movement.
    if (!movementEnabled) return {};
    Vec world=orientation.rotate(gyro);
    // Top surface velocity: omega cross (0,0,R). Sensitivity absorbs radius.
    float x=world.y, y=-world.x;
    float magnitude=std::sqrt(x*x+y*y);
    if (magnitude<=config::MOVEMENT_DEADZONE_RAD_PER_SEC) return {};
    float gain=(magnitude-config::MOVEMENT_DEADZONE_RAD_PER_SEC)/
               (fullSpeed-config::MOVEMENT_DEADZONE_RAD_PER_SEC);
    if (gain>1) gain=1;
    Output out; out.right=x/magnitude*gain; out.forward=y/magnitude*gain;
    return out;
  }
};
} // namespace ball
