#include <cerrno>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <ctime>
#include <algorithm>
struct SDL_Window {};
static struct { bool capFrameRate; unsigned targetFPS; } s_SIM_config;
static uint64_t nowNs,refreshNs;
static unsigned presents;
static int interruptions;
static int fake_clock_gettime(clockid_t,struct timespec *ts) {
    ts->tv_sec=nowNs/1000000000;ts->tv_nsec=nowNs%1000000000;return 0;
}
static int fake_clock_nanosleep(clockid_t,int,const struct timespec *ts,struct timespec *) {
    if(interruptions) { --interruptions;return EINTR; }
    nowNs=std::max(nowNs,(uint64_t)ts->tv_sec*1000000000+(uint64_t)ts->tv_nsec);return 0;
}
static void SDL_GL_SwapWindow(SDL_Window*) {
    if(refreshNs) nowNs=(nowNs/refreshNs+1)*refreshNs;
    ++presents;
}
static void SDL_Log(const char*,...) {}
#define clock_gettime fake_clock_gettime
#define clock_nanosleep fake_clock_nanosleep
#include "android_clock.inc"
static void reset(unsigned fps,unsigned hz) {
    nowNs=1000000000;refreshNs=hz?1000000000/hz:0;presents=0;interruptions=0;
    s_SIM_config={fps!=0,fps};s_androidClock={0};s_androidPresentation={0,0};
    s_androidTimingStart=s_androidTimingLast=s_androidWorkNs=s_androidWaitNs=s_androidSwapNs=0;
    s_androidTicks=s_androidPresents=0;
}
int main() {
    for(unsigned hz: {0u,60u,90u,120u}) for(unsigned fps: {0u,30u,60u,90u,120u}) {
        reset(fps,hz);uint64_t start=nowNs;
        for(unsigned update=0;update<600;update++) {
            nowNs+=1000000;AndroidPaceVBlank();
            nowNs+=4000000;AndroidPaceVBlank();AndroidPresent(nullptr);
        }
        double elapsed=(nowNs-start)/1e9;
        assert(elapsed>19.98 && elapsed<20.04);
        assert(presents>=590 && presents<=600);
    }
    reset(60,60);
    for(int i=0;i<40;i++) { nowNs+=1000000;AndroidPaceVBlank(); }
    uint64_t before=nowNs;
    nowNs+=35000000;AndroidPaceVBlank();
    for(int i=0;i<5;i++) { nowNs+=1000000;AndroidPaceVBlank(); }
    assert(nowNs-before==6*AD_TICK_NS);
    nowNs+=5000000000ULL;before=nowNs;AndroidPaceVBlank();
    assert(nowNs==before);AndroidPaceVBlank();assert(nowNs==before+AD_TICK_NS);
    interruptions=2;before=nowNs;AndroidPaceVBlank();assert(nowNs==before+AD_TICK_NS);
    reset(30,0);
    for(int i=0;i<600;i++) { nowNs+=1000000;AndroidPaceVBlank();AndroidPresent(nullptr); }
    assert(presents==300); // 60 Hz menus: cap presentation without dropping VBlank.
    std::puts("PASS: 30 logic updates/s across 20 display/VSync combinations; stalls, resume, EINTR and 30 FPS presentation cap");
}
