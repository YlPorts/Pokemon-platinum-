/* Execute the real Nitro sound archive and heap code on a 64-bit host.
 * Only OS/device boundaries are stubbed; archive parsing, allocation,
 * linked lists and state disposal are the production implementations. */
#include <assert.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <nitro.h>
#include <nnsys/fnd.h>
#include <nnsys/snd/sndarc.h>
#include <nnsys/snd/player.h>
#include <nnsys/snd/sndarc_player.h>

_Static_assert(sizeof(u32) == 4 && sizeof(s32) == 4, "Nitro integers are 32-bit");
_Static_assert(sizeof(fx32) == 4, "Fixed point is 32-bit");
_Static_assert(sizeof(SNDBinaryFileHeader) == 16, "SDAT file header layout");
_Static_assert(sizeof(SNDBinaryBlockHeader) == 8, "SDAT block header layout");
_Static_assert(sizeof(NNSSndArcHeader) == 48, "SDAT archive header layout");
_Static_assert(offsetof(CARDRomHeader, game_code) == 12, "ROM game code layout");

void MIi_CpuClear32(u32 value, void *dst, u32 size) {
    for (u32 i = 0; i < size / 4; ++i) ((u32 *)dst)[i] = value;
}
u32 SND_GetCurrentCommandTag(void) { return 0; }
BOOL SND_FlushCommand(u32 block) { (void)block; return TRUE; }
void SND_WaitForCommandProc(u32 tag) { (void)tag; }
void SIM_AndroidStartupStage(const char *stage) { (void)stage; }
void WIN_CheckAndFreeAnimBank(void *start, void *end) { (void)start; (void)end; }
void WIN_CheckAndFreeCellBank(void *start, void *end) { (void)start; (void)end; }
void WIN_CheckAndFreeCharData(void *start, void *end) { (void)start; (void)end; }
BOOL FS_IsAvailable(void) { return TRUE; }
void FS_InitFile(FSFile *file) { memset(file, 0, sizeof(*file)); }
BOOL FS_OpenFile(FSFile *file, const char *path) {
    file->pcFilePtr = fopen(path, "rb");
    return file->pcFilePtr != NULL;
}
BOOL FS_SeekFile(FSFile *file, s32 pos, FSSeekFileMode mode) {
    return fseek(file->pcFilePtr, pos, (int)mode) == 0;
}
s32 FS_ReadFile(FSFile *file, void *buffer, s32 count) {
    assert(count >= 0);
    return (s32)fread(buffer, 1, (size_t)count, file->pcFilePtr);
}
BOOL FS_CloseFile(FSFile *file) {
    int result = fclose(file->pcFilePtr);
    file->pcFilePtr = NULL;
    return result == 0;
}

static int disposed;
static void on_dispose(void *memory, u32 size, u64 identity, u32 number) {
    assert(identity == (u64)(uintptr_t)&disposed);
    assert(size == 17 + number);
    assert(((u8 *)memory)[0] == (u8)number);
    ++disposed;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    const size_t heap_size = 8 * 1024 * 1024;
    void *buffer = malloc(heap_size);
    assert(buffer);
    NNSFndHeapHandle expandable = NNS_FndCreateExpHeap(buffer, heap_size);
    assert(expandable);
    void *blocks[128];
    for (int i = 0; i < 128; ++i) {
        blocks[i] = NNS_FndAllocFromExpHeapEx(expandable, 1 + i * 7, i & 1 ? -4 : 4);
        assert(blocks[i]);
        memset(blocks[i], i, 1 + i * 7);
    }
    for (int i = 0; i < 128; ++i) NNS_FndFreeToExpHeap(expandable, blocks[i]);
    NNS_FndDestroyExpHeap(expandable);
    NNSSndHeapHandle heap = NNS_SndHeapCreate(buffer, heap_size);
    assert(heap);
    NNSSndArc arc = {0};
    NNS_SndArcInit(&arc, argv[1], heap, FALSE);
    assert(NNS_SndArcGetCurrent() == &arc && arc.info && arc.fat);
    assert(arc.header.fileHeader.fileSize == 7947008);
    assert(arc.fat->count == 2009);
    assert(NNS_SndArcGetSeqCount() > 100);
    for (u32 i = 0; i < arc.fat->count; ++i) {
        const NNSSndArcFileInfo *entry = &arc.fat->files[i];
        assert(entry->offset <= arc.header.fileHeader.fileSize);
        assert(entry->size <= arc.header.fileHeader.fileSize - entry->offset);
        assert(entry->mem == NULL);
        if (entry->size >= 4) {
            char magic[4];
            assert(NNS_SndArcReadFile(i, magic, 4, 0) == 4);
            assert(memcmp(magic, "SSEQ", 4) == 0 || memcmp(magic, "SSAR", 4) == 0 ||
                   memcmp(magic, "SBNK", 4) == 0 || memcmp(magic, "SWAR", 4) == 0 ||
                   memcmp(magic, "STRM", 4) == 0);
        }
    }
    int players = 0;
    for (int i = 0; i < 16; ++i) {
        const NNSSndArcPlayerInfo *player = NNS_SndArcGetPlayerInfo(i);
        if (player) { assert(player->seqMax <= 16); ++players; }
    }
    assert(players > 0);
    NNSi_SndPlayerInit();
    assert(NNS_SndArcPlayerSetup(heap));
    int baseline = NNS_SndHeapSaveState(heap);
    assert(baseline >= 1);
    for (int pass = 0; pass < 20; ++pass) {
        for (u32 i = 0; i < 64; ++i) {
            u8 *memory = NNS_SndHeapAlloc(heap, 17 + i, on_dispose,
                                         (u64)(uintptr_t)&disposed, i);
            assert(memory && ((uintptr_t)memory % 32) == 0);
            memset(memory, (u8)i, 17 + i);
        }
        NNS_SndHeapLoadState(heap, baseline);
        assert(arc.info && arc.fat);
    }
    assert(disposed == 1280);
    NNS_SndHeapDestroy(heap);
    assert(arc.info == NULL && arc.fat == NULL);
    assert(FS_CloseFile(&arc.file));
    free(buffer);
    printf("PASS: ABI, SDAT 2009 files, %d players, 1280 allocations/disposals\n", players);
    return 0;
}
