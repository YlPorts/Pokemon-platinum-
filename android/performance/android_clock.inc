#include "android_clock.h"
#include <errno.h>
static ADClock s_androidClock={0};
static ADPresentation s_androidPresentation={0,0};
static uint64_t s_androidTimingStart=0,s_androidTimingLast=0;
static uint64_t s_androidWorkNs=0,s_androidWaitNs=0,s_androidSwapNs=0;
static unsigned s_androidTicks=0,s_androidPresents=0;
static uint64_t AndroidNowNs() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC,&ts);
    return (uint64_t)ts.tv_sec*1000000000ULL+(uint64_t)ts.tv_nsec;
}
static void AndroidPaceVBlank() {
    uint64_t now=AndroidNowNs();
    if(!s_androidTimingStart) s_androidTimingStart=now;
    if(s_androidTimingLast) s_androidWorkNs+=now-s_androidTimingLast;
    uint64_t deadline=ad_clock_tick(&s_androidClock,now);
    if(now<deadline) {
        struct timespec target={(time_t)(deadline/1000000000ULL),(long)(deadline%1000000000ULL)};
        while(clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&target,NULL)==EINTR) {}
    }
    uint64_t done=AndroidNowNs();
    s_androidWaitNs+=done-now;
    s_androidTimingLast=done;
    ++s_androidTicks;
    if(done-s_androidTimingStart>=5000000000ULL) {
        double seconds=(done-s_androidTimingStart)/1e9;
        SDL_Log("Android timing: vblank=%.1fHz present=%.1fFPS work=%.2fms wait=%.2fms swap=%.2fms",
            s_androidTicks/seconds,s_androidPresents/seconds,
            s_androidWorkNs/1e6/s_androidTicks,s_androidWaitNs/1e6/s_androidTicks,
            s_androidPresents?s_androidSwapNs/1e6/s_androidPresents:0.0);
        s_androidTimingStart=done;
        s_androidTicks=s_androidPresents=0;
        s_androidWorkNs=s_androidWaitNs=s_androidSwapNs=0;
    }
}
static void AndroidPresent(SDL_Window *target) {
    uint64_t begin=AndroidNowNs();
    unsigned fps=s_SIM_config.capFrameRate ? s_SIM_config.targetFPS : 0;
    if(fps && fps<30) fps=30;
    if(fps>240) fps=240;
    if(ad_present_due(&s_androidPresentation,begin,fps)) {
        SDL_GL_SwapWindow(target);
        uint64_t done=AndroidNowNs();
        s_androidSwapNs+=done-begin;
        ++s_androidPresents;
        s_androidTimingLast=done;
    }
}
