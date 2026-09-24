#include <cassert>
#include <unordered_map>
#include <set>
#include <cstdio>
#include "android_cache_trim.h"
int main() {
 std::unordered_map<unsigned,std::uint64_t> use;
 std::set<unsigned> freed;
 for(unsigned i=0;i<1200;i++) use[i]=i<1000?1:10;
 auto erase=[&](unsigned id) { assert(id<1000); assert(freed.insert(id).second); };
 assert(ad_trim_textures(use,11,erase)==64);
 assert(use.size()==1136);
 assert(ad_trim_textures(use,12,erase)==64);
 assert(ad_trim_textures(use,12,erase)==48);
 assert(use.size()==1024);
 for(unsigned i=1000;i<1200;i++) assert(use.count(i));
 assert(ad_trim_textures(use,20,erase)==0);
 std::unordered_map<unsigned,std::uint64_t> live;
 for(unsigned i=0;i<1100;i++) live[i]=19;
 assert(ad_trim_textures(live,20,erase)==0); // in-flight textures must survive
 puts("PASS: bounded texture eviction, no in-flight deletion or full cache flush");
}
