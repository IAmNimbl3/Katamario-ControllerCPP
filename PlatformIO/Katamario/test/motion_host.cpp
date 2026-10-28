// Host-only regression tests. No board, Arduino runtime or sensor required.
#include "BallMotion.h"
#include "TwistGesture.h"
#include <cassert>
#include <cstdio>
using namespace ball;
bool near(float a,float b,float eps=0.0002f) { return std::abs(a-b)<eps; }
void zero(Output o) { assert(near(o.right,0)); assert(near(o.forward,0)); }
Quat axis(Vec unit,float angle) {
  float s=std::sin(angle/2); return {std::cos(angle/2),unit.x*s,unit.y*s,unit.z*s};
}
int main() {
  TwistGesture gesture;
  auto feed=[&](Vec v,int samples,bool enabled=true) {
    int count=0;
    for(int i=0;i<samples;++i) if(gesture.update(v,0.01f,enabled)) ++count;
    return count;
  };
  assert(feed({0,0,2},50)==0); // Must settle before initial arming.
  assert(feed({},25)==0);
  assert(feed({0,0,0.1f},100)==0); // Noise.
  assert(feed({3,0,2},50)==0); // Rolling dominates the vertical component.
  assert(feed({0,0,2},1)==0); // Single-sample spike.
  assert(feed({},25)==0);
  assert(feed({0,0,2},157)==0); // 179.91 degrees: still below 180.
  assert(feed({0,0,2},1)==1); // Crosses the configured 180-degree threshold.
  assert(feed({0,0,2},200)==0); // Sustained twist is still only one press.
  assert(feed({0,0,-2},50)==0); // Immediate return is not a second press.
  assert(feed({},70)==0);
  assert(feed({0,0,-2},157)==0);
  assert(feed({0,0,-2},1)==1); // Both directions use the same threshold.
  assert(feed({},70)==0);
  assert(feed({0,0,2},100,false)==0); // Never during calibration/demo.
  assert(feed({0,0,2},30)==0); // Reset requires another quiet period.
  std::puts("PASS: twist noise, dominance, spike, hold, release, both directions, calibration reset");
  Motion m;
  zero(m.update({},{0,0,1},0.01f));
  zero(m.update({0.01f,0.01f,0},{0,0,1},0.01f));
  m.reset(); auto slow=m.update({-0.8f,0,0},{},0.01f);
  assert(slow.forward>0 && near(slow.right,0));
  auto fast=m.update({-2.5f,0,0},{},0.01f);
  assert(fast.forward>slow.forward);
  zero(m.update({},{},0.01f)); // No retained velocity after stopping.
  m.reset(); assert(m.update({1,0,0},{},0.01f).forward<0);
  m.reset(); assert(m.update({0,1,0},{},0.01f).right>0);
  m.reset(); assert(m.update({0,-1,0},{},0.01f).right<0);
  m.reset(); zero(m.update({0,0,2},{},0.01f)); // Vertical twist is not translation.
  m.reset(); auto diagonal=m.update({-8,8,0},{},0.01f);
  assert(near(std::sqrt(diagonal.right*diagonal.right+diagonal.forward*diagonal.forward),1));
  assert(near(diagonal.right,diagonal.forward));
  // Independently calculated body readings over ten complete forward turns.
  m.reset();
  for(int i=0;i<10000;++i) {
    float angle=-2*pi*i*0.001f;
    Vec accel(0,std::sin(angle),std::cos(angle));
    auto o=m.update({-2*pi,0,0},accel,0.001f);
    assert(near(o.forward,1)); assert(near(o.right,0));
  }
  // Arbitrary starting pose, including upside-down: same world-frame command.
  const Quat poses[]={axis({1,0,0},pi),axis({0,0,1},pi/2),
                      axis({1,0,0},1.2f)*axis({0,1,0},-0.7f)};
  for (Quat q:poses) {
    m.orientation=q;
    auto o=m.update(q.inverse().rotate({-1,0,0}),q.inverse().rotate({0,0,1}),0.01f);
    assert(o.forward>0.3f); assert(near(o.right,0));
  }
  // Gravity corrects a tilt error while resting, without creating movement.
  m.orientation=axis({1,0,0},0.2f);
  for(int i=0;i<500;++i) zero(m.update({},{0,0,1},0.01f));
  assert(std::abs(m.orientation.x)<0.001f);
  // It must not invent a heading reference from gravity.
  m.orientation=axis({0,0,1},0.7f);
  for(int i=0;i<100;++i) zero(m.update({},{0,0,1},0.01f));
  assert(near(m.orientation.z,std::sin(0.35f)));
  Quat previous=m.orientation;
  zero(m.update({-1,0,0},{},config::MAX_SAMPLE_GAP_SECONDS*2));
  zero(m.update({-1,0,0},{},0));
  assert(near(previous.z,m.orientation.z));
  m.reset(); assert(near(m.orientation.w,1));
  // Alignment preview: orientation tracks a 90-degree turn, movement stays zero.
  for(int i=0;i<100;++i) zero(m.update({0,pi/2,0},{},0.01f,false));
  assert(near(m.orientation.w,std::cos(pi/4)));
  assert(near(m.orientation.y,std::sin(pi/4)));
  assert(near(m.orientation.x,0) && near(m.orientation.z,0));
  assert(m.update({0,1,0},{},0.01f,true).right>0);
  m.reset();
  assert(near(m.orientation.w,1) && near(m.orientation.y,0));
  std::puts("PASS: stop, noise, direction, speed, diagonal, twist, 10 turns, frame transform, tilt, yaw, timing, reset, alignment preview");
}
