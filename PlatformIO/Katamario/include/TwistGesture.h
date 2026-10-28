#pragma once
#include "BallMotion.h"

namespace ball {
// One pulse per twist; must settle before rearming. No movement output changes.
class TwistGesture {
  bool armed=false;
  float quiet=0, angle=0, cooldown=0;
  int direction=0;
 public:
  void reset() { armed=false; quiet=angle=cooldown=0; direction=0; }
  bool update(Vec worldGyro, float dt, bool enabled) {
    if (!enabled || !(dt>0 && dt<=config::MAX_SAMPLE_GAP_SECONDS)) {
      reset(); return false;
    }
    cooldown=std::fmax(0.0f,cooldown-dt);
    const float vertical=std::abs(worldGyro.z);
    const float horizontal=std::sqrt(worldGyro.x*worldGyro.x+worldGyro.y*worldGyro.y);
    if (!armed) {
      quiet=vertical<config::TWIST_RELEASE_RAD_PER_SEC ? quiet+dt : 0;
      if (quiet>=config::TWIST_RELEASE_SECONDS && cooldown<=0) armed=true;
      return false;
    }
    if (vertical<config::TWIST_TRIGGER_RAD_PER_SEC ||
        vertical<config::TWIST_VERTICAL_DOMINANCE*horizontal) {
      angle=0; direction=0; return false;
    }
    const int sign=worldGyro.z>0 ? 1 : -1;
    if (sign!=direction) { angle=0; direction=sign; }
    angle+=vertical*dt;
    if (angle<config::TWIST_MIN_ANGLE_RAD) return false;
    armed=false; quiet=angle=0; direction=0;
    cooldown=config::TWIST_COOLDOWN_SECONDS;
    return true;
  }
};
}
