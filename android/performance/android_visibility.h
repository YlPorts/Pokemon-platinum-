#ifndef ANDROID_VISIBILITY_H
#define ANDROID_VISIBILITY_H
/* Only presentation is culled. Game logic, 3D commands, audio and VBlank still run. */
static inline int ad_engine_visible(int single,int bottom,int mainOnTop,int isSub) {
    return !single || bottom==(isSub ? mainOnTop : !mainOnTop);
}
#endif
