// Cached decoding only. Transformations, lighting and draw commands still run
// on every replay with current state. No rendered frames or animations cached.
#include <vector>
#include <cstring>
struct ADCommandEntry {
    const void *address=nullptr;
    uint64_t age=0;
    bool bypass=false;
    std::vector<u8> bytes;
    std::vector<draw_msg_t> commands;
};
static ADCommandEntry s_androidCommands[32];
static uint64_t s_androidCommandAge=0;
static unsigned s_androidListHits=0,s_androidListMisses=0;
static uint64_t s_androidListNs=0;
static const size_t AD_LIST_LIMIT=1024*1024; // max decoded bytes per entry
template<class Emit> static bool AndroidDecodeCommands(const u8 *data,size_t size,Emit emit) {
    size_t offset=0;
    while(offset<size) {
        if(size-offset<4) return false;
        u8 ops[4]; memcpy(ops,data+offset,4); offset+=4;
        for(unsigned op=0;op<4;++op) {
            draw_msg_t msg={};
            msg.type=DecodeG3Op(ops[op]);
            unsigned n=GetNumParamsFromCommandType(msg.type);
            unsigned width=GetParamSizeFromCommandType(msg.type);
            bool sign=isParamSigned(msg.type)!=0;
            if(n>32 || n*width>size-offset) return false;
            for(unsigned p=1;p<=n;++p) {
                uint64_t value=0;
                if(width) memcpy(&value,data+offset,width);
                offset+=width;
                if(sign && width && width<8) {
                    unsigned bits=width*8;
                    uint64_t mask=UINT64_C(1)<<(bits-1);
                    value=(value^mask)-mask;
                }
                msg.data.numsU64[p]=value;
            }
            ConvertMsgParams(&msg);
            if(!emit(msg)) return false;
        }
    }
    return true;
}
extern "C" void SIM_HandleG3CommandList(const void *data,u32 size) {
#ifdef AD_COMMAND_PROFILE
    struct Timer {uint64_t begin=AndroidNowNs();~Timer(){s_androidListNs+=AndroidNowNs()-begin;}} timer;
#endif
    if(!size) return;
    if(!data) return;
    const u8 *bytes=(const u8*)data;
    ADCommandEntry *entry=nullptr,*oldest=&s_androidCommands[0];
    for(auto &e:s_androidCommands) {
        if(e.address==data && e.bytes.size()==size) {entry=&e;break;}
        if(e.age<oldest->age) oldest=&e;
    }
    if(entry && memcmp(entry->bytes.data(),bytes,size)==0) {
        if(!entry->bypass) ++s_androidListHits;
        else ++s_androidListMisses;
    } else {
        ++s_androidListMisses;
        entry=entry?entry:oldest;
        entry->address=nullptr;entry->age=0;entry->bypass=false;
        // Release previous capacity too: bound retained memory, including misses.
        std::vector<u8>().swap(entry->bytes);
        std::vector<draw_msg_t>().swap(entry->commands);
        bool cached=false;
        if(size<=65536) {
            entry->bytes.assign(bytes,bytes+size);
            cached=AndroidDecodeCommands(entry->bytes.data(),size,[&](const draw_msg_t &m) {
                if((entry->commands.size()+1)*sizeof(m)>AD_LIST_LIMIT/2) return false;
                entry->commands.push_back(m); return true;
            });
        }
        if(!cached) {
            std::vector<draw_msg_t>().swap(entry->commands);
            entry->bypass=true;
        }
        entry->address=data;
    }
    entry->age=++s_androidCommandAge;
    if(entry->bypass) {
        AndroidDecodeCommands(bytes,size,[](draw_msg_t &m){SIM_HandleG3Command(&m);return true;});
        return;
    }
    for(const auto &cached:entry->commands) {
        // The interpreter mutates partial-vertex commands. Never pass the cache
        // itself: VTX_DIFF/XY/XZ/YZ must use this replay's previous vertex.
        draw_msg_t command=cached;
        SIM_HandleG3Command(&command);
    }
}
