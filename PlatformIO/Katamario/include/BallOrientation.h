#pragma once
#include "BallMotion.h"

namespace ball {
// Physical mounting calibration, not game sensitivity. Bias/matrix are in the
// magnetometer frame; mounting then maps that frame into MPU6050 body axes.
struct MagneticCalibration {
  bool valid=false;
  Vec biasMicrotesla;
  Vec matrixRows[3]={{1,0,0},{0,1,0},{0,0,1}};
  Quat mounting;
  Vec apply(Vec raw) const {
    Vec v=raw-biasMicrotesla;
    auto dot=[&](Vec row) { return row.x*v.x+row.y*v.y+row.z*v.z; };
    return mounting.rotate({dot(matrixRows[0]),dot(matrixRows[1]),dot(matrixRows[2])});
  }
};

// Optional yaw-only aiding of Motion's existing quaternion. Does not integrate
// gyro, infer screen direction, detect gestures, or replace gravity correction.
class BallOrientation {
 public:
  enum class State { Disabled, Uncalibrated, Waiting, Referenced, Corrected, Rejected };
  struct Settings {
    bool enabled=false;
    float gainPerSecond=0.5f;
    float fieldSmoothingSeconds=0; // Optional low-pass in world frame while near rest.
    float maxCorrectionRadPerSecond=0.05f;
    float maxGyroRadPerSecond=0.15f;
    float quietSecondsBeforeCorrection=2.5f;
    float stableFieldAngleRad=3.0f*pi/180.0f;
    float stableRelativeFieldChange=0.05f;
    float minFieldMicrotesla=10, maxFieldMicrotesla=100;
    float minHorizontalMicrotesla=5;
    float maxRelativeFieldChange=0.2f;
    float maxHeadingErrorRad=pi/4;
    unsigned referenceSamples=30;
  } settings;
  MagneticCalibration calibration;

  void reset() {
    reference_={}; strength_=0; hasReference_=false;
    missingSample();
  }
  State state() const { return state_; }
  float stableSeconds() const { return stableSeconds_; }
  void missingSample() { resetWindow(); filtered_=false; state_=State::Waiting; }
  // Observe EVERY MPU sample, including when no new magnetic reading exists.
  // A short movement between magnetometer samples must restart the dwell too.
  void observeGyro(Vec gyro) {
    if (!(gyro.norm()<=settings.maxGyroRadPerSecond)) missingSample();
  }

  // Only feed newly acquired samples and their own elapsed time, never cached
  // data. The caller resets this object when the player's alignment is reset.
  bool update(Quat &orientation,Vec raw,Vec gyro,float dt) {
    if (!settings.enabled) { resetWindow(); state_=State::Disabled; return false; }
    if (!calibration.valid) { resetWindow(); state_=State::Uncalibrated; return false; }
    Vec body=calibration.apply(raw);
    float norm=body.norm();
    if (!(dt>0 && dt<=config::MAX_SAMPLE_GAP_SECONDS) ||
        !std::isfinite(norm) || !(gyro.norm()<=settings.maxGyroRadPerSecond) ||
        norm<settings.minFieldMicrotesla || norm>settings.maxFieldMicrotesla) return reject();
    Vec world=orientation.rotate(body);
    if (settings.fieldSmoothingSeconds>0) {
      const float alpha=1-std::exp(-dt/settings.fieldSmoothingSeconds);
      filteredWorld_=filtered_ ? filteredWorld_+(world-filteredWorld_)*alpha : world;
      filtered_=true; world=filteredWorld_; norm=world.norm();
    }
    const float horizontal=std::sqrt(world.x*world.x+world.y*world.y);
    if (!std::isfinite(world.norm()) || !std::isfinite(horizontal) ||
        horizontal<settings.minHorizontalMicrotesla) return reject();
    if (!hasReference_) {
      sum_=sum_+world;
      if (++count_ < settings.referenceSamples) { state_=State::Waiting; return false; }
      reference_=sum_*(1.0f/count_);
      strength_=reference_.norm();
      if (strength_<settings.minFieldMicrotesla ||
          std::hypot(reference_.x,reference_.y)<settings.minHorizontalMicrotesla) return reject();
      hasReference_=true; resetWindow(); state_=State::Referenced;
      return false; // Preserve player's starting heading; do not snap to north.
    }
    if (std::abs(norm-strength_)>strength_*settings.maxRelativeFieldChange) return reject();
    const float error=std::atan2(world.x*reference_.y-world.y*reference_.x,
                                world.x*reference_.x+world.y*reference_.y);
    if (!std::isfinite(error) || std::abs(error)>settings.maxHeadingErrorRad) return reject();
    // Compare the gravity-compensated world field with the start of the quiet
    // window. Real slow rotation is removed by the MPU orientation, so it does
    // not masquerade as a magnetic disturbance. Do not compare raw body axes.
    if (!windowStarted_) startWindow(world,norm);
    else {
      const Vec direction=world*(1.0f/world.norm());
      const float dot=direction.x*windowDirection_.x+direction.y*windowDirection_.y+
                      direction.z*windowDirection_.z;
      if (dot<std::cos(settings.stableFieldAngleRad) ||
          std::abs(norm-windowStrength_)>windowStrength_*settings.stableRelativeFieldChange) {
        // This reading can start a new window, but contributes no elapsed time.
        startWindow(world,norm); state_=State::Waiting; return false;
      }
      stableSeconds_+=dt;
    }
    if (stableSeconds_<settings.quietSecondsBeforeCorrection) {
      state_=State::Waiting; return false;
    }
    stableSeconds_=settings.quietSecondsBeforeCorrection; // Bound long sessions.
    float step=error*(1-std::exp(-settings.gainPerSecond*dt));
    const float limit=settings.maxCorrectionRadPerSecond*dt;
    if(step>limit) step=limit;
    if(step< -limit) step= -limit;
    // Left multiplication: rotate around WORLD up, preserving measured tilt.
    const Quat correction(std::cos(step/2),0,0,std::sin(step/2));
    orientation=correction*orientation;
    // Keep the stability window in the corrected frame. Our own correction
    // must not look like a magnetic disturbance on the following sample.
    windowDirection_=correction.rotate(windowDirection_);
    if (filtered_) filteredWorld_=correction.rotate(filteredWorld_);
    orientation.normalize(); state_=State::Corrected;
    return true;
  }
 private:
  void resetWindow() {
    sum_={}; count_=0; stableSeconds_=0; windowStarted_=false;
  }
  void startWindow(Vec world,float strength) {
    windowDirection_=world*(1.0f/world.norm()); windowStrength_=strength;
    stableSeconds_=0; windowStarted_=true;
  }
  bool reject() { resetWindow(); filtered_=false; state_=State::Rejected; return false; }
  Vec reference_,sum_,filteredWorld_;
  bool filtered_=false;
  Vec windowDirection_;
  float windowStrength_=0,stableSeconds_=0;
  float strength_=0;
  unsigned count_=0;
  bool hasReference_=false;
  bool windowStarted_=false;
  State state_=State::Waiting;
};
} // namespace ball
