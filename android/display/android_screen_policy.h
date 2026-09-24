#ifndef ANDROID_SCREEN_POLICY_H
#define ANDROID_SCREEN_POLICY_H
#include <stdint.h>
typedef struct { uint32_t last; int manual; } ADScreenPolicy;
static inline int ad_selected_screen(ADScreenPolicy *p, int bottom, uint32_t generation) {
    uint32_t token=(generation<<1)|(bottom!=0);
    if(p->last!=token) { p->last=token; p->manual=-1; }
    return p->manual<0?bottom:p->manual;
}
#endif
