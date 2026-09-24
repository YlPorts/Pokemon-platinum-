#ifndef ANDROID_SCREEN_POLICY_H
#define ANDROID_SCREEN_POLICY_H
#include <stdint.h>
typedef struct { uint32_t last; int manual; } ADScreenPolicy;
static inline int ad_selected_screen(ADScreenPolicy *p, int bottom, uint32_t generation) {
    uint32_t token=(generation<<1)|(bottom!=0);
    if(p->last!=token) { p->last=token; p->manual=-1; }
    return p->manual<0?bottom:p->manual;
}
typedef struct { int shown, candidate; uint32_t since, generation; } ADScreenTransition;
static inline int ad_automatic_screen(ADScreenTransition *s, int requested, uint32_t generation, uint32_t now) {
    if(s->shown<0 || s->generation!=generation) {
        s->shown=s->candidate=requested; s->generation=generation; s->since=now;
    } else if(s->candidate!=requested) {
        s->candidate=requested; s->since=now;
    } else if((uint32_t)(now-s->since)>=80) s->shown=requested;
    return s->shown;
}
#endif
