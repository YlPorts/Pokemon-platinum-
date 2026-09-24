#ifndef ANDROID_CACHE_TRIM_H
#define ANDROID_CACHE_TRIM_H
#include <cstddef>
#include <cstdint>
/* Never evict current/previous frame textures: deferred translucent draws may
   still reference them. Bound deletion/upload churn when entering a new map. */
template<class UsageMap, class Erase>
static std::size_t ad_trim_textures(UsageMap &usage, std::uint64_t frame, Erase erase) {
    std::size_t removed=0;
    for(auto it=usage.begin(); usage.size()>1024 && removed<64 && it!=usage.end();) {
        if(frame>it->second && frame-it->second>2) {
            erase(it->first); it=usage.erase(it); ++removed;
        } else ++it;
    }
    return removed;
}
#endif
