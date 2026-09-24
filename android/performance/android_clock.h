#ifndef ANDROID_GAME_CLOCK_H
#define ANDROID_GAME_CLOCK_H
#include <stdint.h>
/* The DS runs 60 VBlank slices/s; the field loop consumes two per update.
   Display caps never modify this clock. Keep deadlines across swap waits. */
typedef struct { uint64_t next; } ADClock;
#define AD_TICK_NS UINT64_C(16666667)
static inline uint64_t ad_clock_tick(ADClock *clock,uint64_t now) {
    if(!clock->next) clock->next=now;
    if(now>clock->next && now-clock->next>3*AD_TICK_NS)
        clock->next=now-AD_TICK_NS; /* resume/long stall: no catch-up burst */
    clock->next+=AD_TICK_NS;
    return clock->next;
}
typedef struct { uint64_t next; unsigned fps; } ADPresentation;
static inline int ad_present_due(ADPresentation *p,uint64_t now,unsigned fps) {
    if(!fps) { p->next=0;p->fps=0;return 1; }
    if(p->fps!=fps) { p->next=0;p->fps=fps; }
    uint64_t period=UINT64_C(1000000000)/fps;
    if(p->next && now+UINT64_C(1000000)<p->next) return 0;
    if(!p->next || now>p->next+period) p->next=now;
    p->next+=period;
    return 1;
}
#endif
