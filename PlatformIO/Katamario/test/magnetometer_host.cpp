#include "Ak09911.h"
#include "BallOrientation.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <vector>
using namespace ball;
bool near(float a,float b,float epsilon=0.0001f) { return std::abs(a-b)<epsilon; }
Quat axis(Vec v,float a) { float s=std::sin(a/2); return {std::cos(a/2),v.x*s,v.y*s,v.z*s}; }
struct Bus : MagnetometerBus {
  uint8_t target=0x0c, id=5, mode=0, status=1, overflow=0;
  bool fail=false, failBurst=false, wrongMode=false;
  unsigned reads=0, bursts=0, waits=0;
  std::vector<unsigned> modes;
  bool read(uint8_t a,uint8_t reg,uint8_t *data,uint8_t size) override {
    ++reads;
    if(fail || a!=target) return false;
    if(reg==0 && size==2) { data[0]=0x48; data[1]=id; }
    else if(reg==0x60 && size==3) { assert(mode==0x1f); data[0]=0; data[1]=128; data[2]=64; }
    else if(reg==0x31 && size==1) data[0]=wrongMode?0:mode;
    else if(reg==0x10 && size==1) data[0]=status;
    else if(reg==0x11 && size==8) {
      ++bursts;
      if(failBurst) return false;
      int16_t values[]={100,-200,300};
      for(int i=0;i<3;++i) { data[i*2]=uint16_t(values[i])&255; data[i*2+1]=uint16_t(values[i])>>8; }
      data[6]=0; data[7]=overflow;
    } else assert(false);
    return true;
  }
  bool write(uint8_t a,uint8_t reg,uint8_t value) override {
    if(fail || a!=target) return false;
    if(reg==0x31) { mode=value; modes.push_back(value); }
    else { assert(reg==0x32 && value==1); mode=0; }
    return true;
  }
  void waitMicros(uint32_t us) override { assert(us>=100); ++waits; }
};
int main() {
  Bus bus; Ak09911 sensor(bus); Vec field(9,9,9);
  assert(sensor.read(field)==Ak09911::Result::Offline && bus.reads==0);
  assert(sensor.begin() && sensor.address()==0x0c && bus.waits>=4);
  assert((bus.modes==std::vector<unsigned>{0,31,0,0,8}));
  assert(sensor.read(field)==Ak09911::Result::Sample);
  assert(near(field.x,60) && near(field.y,-240) && near(field.z,270));
  bus.status=0; auto before=bus.bursts;
  assert(sensor.read(field)==Ak09911::Result::NotReady && bus.bursts==before);
  bus.status=3; // DRDY + DOR: consume current valid reading.
  assert(sensor.read(field)==Ak09911::Result::Sample);
  bus.overflow=8; field={9,9,9};
  assert(sensor.read(field)==Ak09911::Result::Overflow && field.x==9);
  bus.failBurst=true;
  assert(sensor.read(field)==Ak09911::Result::IoError && !sensor.online());
  before=bus.reads; assert(sensor.read(field)==Ak09911::Result::Offline && bus.reads==before);
  Bus alternate; alternate.target=0x0d; Ak09911 second(alternate); assert(second.begin());
  alternate.id=4; assert(!second.begin());
  alternate.id=5; alternate.wrongMode=true; assert(!second.begin());
  std::puts("PASS: AK09911 identity, both addresses, mode transitions, factory scale, signed axes, ST2, missing data, overflow and I2C failures");

  BallOrientation aid; Quat q;
  aid.settings.quietSecondsBeforeCorrection=0; // Isolate math; dwell tested below.
  assert(!aid.update(q,{30,0,20},{},.01f) && q.w==1);
  aid.settings.enabled=true;
  assert(!aid.update(q,{30,0,20},{},.01f));
  assert(aid.state()==BallOrientation::State::Uncalibrated);
  aid.calibration.valid=true;
  for(int i=0;i<30;++i) assert(!aid.update(q,{30,0,20},{},.01f));
  assert(aid.state()==BallOrientation::State::Referenced);
  q=axis({0,0,1},.2f);
  aid.update(q,{30,0,20},{},.01f);
  assert(q.z<std::sin(.1f)); // Correct sign, toward initial heading.
  assert(2*std::acos(q.w)>.199f); // Bounded correction, no snap.
  for(int i=0;i<1500;++i) aid.update(q,{30,0,20},{},.01f);
  assert(std::abs(q.z)<.001f);
  q=axis({0,0,1},-.2f);
  for(int i=0;i<1500;++i) aid.update(q,{30,0,20},{},.01f);
  assert(std::abs(q.z)<.001f);
  // Real tilt is accounted for and preserved by world-Z correction.
  Quat tilt=axis({1,0,0},.7f)*axis({0,1,0},-.4f);
  Vec tiltedField=tilt.inverse().rotate({30,0,20});
  q=axis({0,0,1},.2f)*tilt;
  Vec gravity=q.inverse().rotate({0,0,1});
  for(int i=0;i<1000;++i) aid.update(q,tiltedField,{},.01f);
  Vec after=q.inverse().rotate({0,0,1});
  assert((after-gravity).norm()<.0001f);
  assert((q.rotate(tiltedField)-Vec(30,0,20)).norm()<.1f);
  auto unchanged=[&](Vec mag,Vec gyro,float dt) {
    Quat old=q; assert(!aid.update(q,mag,gyro,dt));
    assert(q.w==old.w && q.x==old.x && q.y==old.y && q.z==old.z);
  };
  unchanged({300,0,20},{},.01f); // Interference magnitude.
  unchanged({0,0,0},{},.01f);
  unchanged({std::numeric_limits<float>::quiet_NaN(),0,0},{},.01f);
  unchanged(tiltedField,{1,0,0},.01f); // No correction during rolling.
  unchanged(tiltedField,{},.1f); // No stale/gapped integration.
  unchanged(tiltedField,{},0);
  aid.reset(); q=Quat();
  for(int i=0;i<29;++i) aid.update(q,{30,0,20},{},.01f);
  aid.missingSample();
  aid.update(q,{30,0,20},{},.01f);
  assert(aid.state()==BallOrientation::State::Waiting); // Requires consecutive samples.
  aid.reset(); q=axis({0,0,1},1.2f); Quat initial=q;
  for(int i=0;i<30;++i) aid.update(q,{30,0,20},{},.01f);
  assert(q.w==initial.w && q.z==initial.z); // Never snaps player heading to north.
  q=axis({0,0,1},2.2f); unchanged({30,0,20},{},.01f); // Large angle disturbance.
  MagneticCalibration cal; cal.biasMicrotesla={10,20,30};
  cal.matrixRows[0]={2,0,0}; cal.mounting=axis({0,0,1},pi/2);
  assert((cal.apply({11,20,30})-Vec(0,2,0)).norm()<.0001f);
  std::puts("PASS: disabled/unconfigured fallback, reference capture/reset, bidirectional yaw correction, tilt preservation, interference, gaps and mounting calibration");

  BallOrientation seamless;
  seamless.settings.enabled=true; seamless.calibration.valid=true;
  Quat pose;
  const Vec north(30,0,20);
  for(int i=0;i<30;++i) seamless.update(pose,north,{},.01f);
  const Quat actual=axis({0,0,1},40*pi/180);
  const Vec reading=actual.inverse().rotate(north);
  pose=axis({0,0,1},45*pi/180); // Real heading 40 degrees, estimate 45.
  auto waitWithoutChange=[&](int samples,Vec mag,float dt=.01f) {
    const Quat old=pose;
    for(int i=0;i<samples;++i) assert(!seamless.update(pose,mag,{},dt));
    assert(pose.w==old.w && pose.x==old.x && pose.y==old.y && pose.z==old.z);
  };
  waitWithoutChange(240,reading); // No correction before 2.5 seconds.
  assert(seamless.stableSeconds()>2.3f);
  seamless.observeGyro({0,0,1}); // Even if this MPU sample had no magnetic data.
  assert(seamless.stableSeconds()==0);
  waitWithoutChange(240,reading);
  bool corrected=false;
  for(int i=0;i<20;++i) corrected=seamless.update(pose,reading,{},.01f)||corrected;
  assert(corrected);
  for(int i=0;i<1600;++i) assert(seamless.update(pose,reading,{},.01f));
  assert(std::abs(2*std::atan2(pose.z,pose.w)-40*pi/180)<.001f);
  // Sustained correction does not reset its own stability window.
  assert(seamless.state()==BallOrientation::State::Corrected);
  seamless.missingSample(); waitWithoutChange(240,reading);
  // Stable-looking magnitude alone is insufficient: rotating field resets dwell.
  Vec disturbance=axis({0,0,1},.12f).rotate(reading);
  waitWithoutChange(1,disturbance);
  assert(seamless.stableSeconds()==0);
  waitWithoutChange(1,reading);
  waitWithoutChange(230,reading);
  waitWithoutChange(1,reading*1.08f); // >5% window tolerance, within 20% global gate.
  assert(seamless.stableSeconds()==0);
  waitWithoutChange(1,reading);
  waitWithoutChange(230,reading);
  assert(!seamless.update(pose,reading,{},.1f));
  assert(seamless.stableSeconds()==0);
  waitWithoutChange(230,reading);
  seamless.settings.enabled=false;
  assert(!seamless.update(pose,reading,{},.01f));
  seamless.settings.enabled=true;
  waitWithoutChange(230,reading);
  seamless.calibration.valid=false;
  assert(!seamless.update(pose,reading,{},.01f));
  seamless.calibration.valid=true;
  waitWithoutChange(230,reading);
  // A changed sample rate measures seconds, not counts.
  seamless.missingSample(); waitWithoutChange(120,reading,.02f);
  corrected=false;
  for(int i=0;i<10;++i) corrected=seamless.update(pose,reading,{},.02f)||corrected;
  assert(corrected);
  // Real slow rotation is stable in world coordinates even while body axes turn.
  seamless.reset(); pose=Quat();
  for(int i=0;i<30;++i) seamless.update(pose,north,{},.01f);
  corrected=false;
  for(int i=0;i<300;++i) {
    pose=axis({0,0,1},i*.001f);
    corrected=seamless.update(pose,pose.inverse().rotate(north),{0,0,.1f},.01f)||corrected;
  }
  assert(corrected);
  assert(std::abs(2*std::atan2(pose.z,pose.w)-.299f)<.0001f);
  std::puts("PASS: 2.5-second dwell, brief movement reset, magnetic direction/strength stability, interruption, sample rates and real heading preservation");
}
