#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <vector>
// Exact byte comparison, not a pointer-only cache: writes to VRAM/palettes
// within the same frame invalidate the result immediately. Bounded to 2 MiB.
struct ADCrcMemo {
    struct Entry { const uint8_t *ptr=nullptr; uint32_t crc=0; std::vector<uint8_t> bytes; };
    Entry entries[16];
    template<class Hash> uint32_t get(const uint8_t *ptr,size_t size,Hash hash) {
        if(size>128*1024) return hash(ptr,size);
        uintptr_t key=(uintptr_t)ptr;
        Entry &e=entries[((key>>4)^(key>>12)^size)&15];
        if(e.ptr==ptr && e.bytes.size()==size && (!size || memcmp(e.bytes.data(),ptr,size)==0)) return e.crc;
        uint32_t crc=hash(ptr,size);
        e.bytes.assign(ptr,ptr+size); e.ptr=ptr; e.crc=crc;
        return crc;
    }
};
