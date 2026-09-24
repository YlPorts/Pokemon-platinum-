#include "android_clock.h"
#include <errno.h>
static ADClock s_androidClock={0};
static ADPresentation s_androidPresentation={0,0};
static uint64_t s_androidTimingStart=0,s_androidTimingLast=0;
static uint64_t s_androidWorkNs=0,s_androidWaitNs=0,s_androidSwapNs=0;
static unsigned s_androidTicks=0,s_androidPresents=0;
static uint64_t s_androidComposeNs=0,s_androidLastPresent=0;
static unsigned s_androidComposes=0;
static void AndroidTimingWrite(const char *line) {
    SDL_Log("%s",line);
#ifdef SDK_BUILD_ANDROID
    FILE *f=fopen("android_performance.log","a+");
    if(!f) return;
    fseek(f,0,SEEK_END);
    if(ftell(f)>65536) {
        fclose(f);
        rename("android_performance.log","android_performance.previous.log");
        f=fopen("android_performance.log","w");
        if(!f) return;
    }
    fprintf(f,"%lld %s\n",(long long)time(NULL),line);
    fclose(f);
#endif
}
static uint64_t AndroidNowNs() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC,&ts);
    return (uint64_t)ts.tv_sec*1000000000ULL+(uint64_t)ts.tv_nsec;
}
static void AndroidPaceVBlank() {
    uint64_t now=AndroidNowNs();
    if(!s_androidTimingStart) {
        s_androidTimingStart=now;
#ifdef SDK_BUILD_ANDROID
        char header[512];
        snprintf(header,sizeof(header),"SESSION Android 0.3.6 GPU=%s GL=%s",glGetString(GL_RENDERER),glGetString(GL_VERSION));
        AndroidTimingWrite(header);
#endif
    }
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
    if(done-s_androidTimingStart>=2000000000ULL) {
        double seconds=(done-s_androidTimingStart)/1e9;
        char report[512];
        snprintf(report,sizeof(report),"Android timing: vblank=%.1fHz present=%.1fFPS work=%.2fms wait=%.2fms swap=%.2fms compose=%.2fms",
            s_androidTicks/seconds,s_androidPresents/seconds,
            s_androidWorkNs/1e6/s_androidTicks,s_androidWaitNs/1e6/s_androidTicks,
            s_androidPresents?s_androidSwapNs/1e6/s_androidPresents:0.0,
            s_androidComposes?s_androidComposeNs/1e6/s_androidComposes:0.0);
        AndroidTimingWrite(report);
        s_androidTimingStart=done;
        s_androidTicks=s_androidPresents=0;
        s_androidWorkNs=s_androidWaitNs=s_androidSwapNs=0;
        s_androidComposeNs=s_androidComposes=0;
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
#ifdef SDK_BUILD_ANDROID
        if(s_androidLastPresent) s_SIM_frameTime=done-s_androidLastPresent;
#endif
        s_androidLastPresent=done;
        s_androidSwapNs+=done-begin;
        ++s_androidPresents;
        s_androidTimingLast=done;
    }
}
