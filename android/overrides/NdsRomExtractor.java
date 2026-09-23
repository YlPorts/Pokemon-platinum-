package org.pokeplatinum.android;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Extracts the NitroFS file tree from a Pokémon Platinum USA .nds file. */
final class NdsRomExtractor {
    interface Progress {
        void onFiles(int done, int total);
    }

    private static final long MAX_ROM_SIZE = 512L * 1024 * 1024;
    private static final long MAX_EXTRACTED_SIZE = 1024L * 1024 * 1024;
    private static final int MAX_DIRECTORIES = 4096;

    private static final class Entry {
        final int directory;
        final int id;
        final String name;

        Entry(int directory, int id, String name) {
            this.directory = directory;
            this.id = id;
            this.name = name;
        }
    }

    private NdsRomExtractor() {}

    static int extract(File romFile, File outputDirectory, Progress progress) throws IOException {
        try (RandomAccessFile rom = new RandomAccessFile(romFile, "r")) {
            long romSize = rom.length();
            if (romSize < 0x200 || romSize > MAX_ROM_SIZE) {
                throw new IOException("la ROM tiene un tamaño no válido");
            }
            byte[] header = new byte[0x200];
            rom.readFully(header);
            String gameCode = new String(header, 0x0c, 4, StandardCharsets.US_ASCII);
            if (!"CPUE".equals(gameCode)) {
                throw new IOException("se necesita una ROM de Pokémon Platinum USA (CPUE)");
            }

            long fntOffset = u32(header, 0x40);
            long fntSize = u32(header, 0x44);
            long fatOffset = u32(header, 0x48);
            long fatSize = u32(header, 0x4c);
            checkRegion(fntOffset, fntSize, romSize);
            checkRegion(fatOffset, fatSize, romSize);
            if (fntSize < 8 || fatSize == 0 || fatSize % 8 != 0 || fatSize / 8 > 65536) {
                throw new IOException("tablas de archivos de la ROM no válidas");
            }

            int fatCount = (int) (fatSize / 8);
            long[] starts = new long[fatCount];
            long[] ends = new long[fatCount];
            rom.seek(fatOffset);
            for (int i = 0; i < fatCount; i++) {
                starts[i] = readU32(rom);
                ends[i] = readU32(rom);
                if (ends[i] < starts[i] || ends[i] > romSize) {
                    throw new IOException("entrada FAT fuera de la ROM");
                }
            }

            rom.seek(fntOffset);
            readU32(rom);
            readU16(rom);
            int count = readU16(rom);
            if (count < 1 || count > MAX_DIRECTORIES || (long) count * 8 > fntSize) {
                throw new IOException("tabla de directorios no válida");
            }
            long[] nameOffsets = new long[count];
            int[] firstIds = new int[count];
            int[] parents = new int[count];
            String[] names = new String[count];
            names[0] = "";
            rom.seek(fntOffset);
            for (int i = 0; i < count; i++) {
                nameOffsets[i] = readU32(rom);
                firstIds[i] = readU16(rom);
                parents[i] = readU16(rom) & 0x0fff;
                if (nameOffsets[i] < (long) count * 8 || nameOffsets[i] >= fntSize) {
                    throw new IOException("directorio fuera de la tabla FNT");
                }
            }

            List<Entry> entries = new ArrayList<>();
            boolean[] seenIds = new boolean[fatCount];
            long fntEnd = fntOffset + fntSize;
            for (int directory = 0; directory < count; directory++) {
                rom.seek(fntOffset + nameOffsets[directory]);
                int fileId = firstIds[directory];
                boolean terminated = false;
                while (rom.getFilePointer() < fntEnd) {
                    int tag = rom.readUnsignedByte();
                    if (tag == 0) {
                        terminated = true;
                        break;
                    }
                    int length = tag & 0x7f;
                    boolean subdirectory = (tag & 0x80) != 0;
                    if (length == 0 || rom.getFilePointer() + length + (subdirectory ? 2 : 0) > fntEnd) {
                        throw new IOException("nombre de archivo fuera de la tabla FNT");
                    }
                    byte[] bytes = new byte[length];
                    rom.readFully(bytes);
                    String name = safeName(bytes);
                    if (subdirectory) {
                        int rawId = readU16(rom);
                        int child = rawId & 0x0fff;
                        if ((rawId & 0xf000) != 0xf000 || child == 0 || child >= count
                                || parents[child] != directory || names[child] != null) {
                            throw new IOException("árbol de carpetas de la ROM no válido");
                        }
                        names[child] = name;
                    } else {
                        if (fileId >= fatCount || seenIds[fileId]) {
                            throw new IOException("identificador de archivo no válido");
                        }
                        seenIds[fileId] = true;
                        entries.add(new Entry(directory, fileId++, name));
                    }
                }
                if (!terminated) {
                    throw new IOException("directorio de la ROM sin terminar");
                }
            }
            for (int i = 1; i < count; i++) {
                if (names[i] == null) {
                    throw new IOException("carpeta de la ROM sin nombre");
                }
            }
            if (entries.isEmpty()) {
                throw new IOException("la ROM no contiene archivos del juego");
            }

            if (!outputDirectory.isDirectory() && !outputDirectory.mkdirs()) {
                throw new IOException("no se pudo preparar la carpeta de extracción");
            }
            try (FileOutputStream output = new FileOutputStream(new File(outputDirectory, "header.bin"))) {
                output.write(header);
            }
            Set<String> paths = new HashSet<>();
            long totalBytes = 0;
            byte[] buffer = new byte[64 * 1024];
            for (int i = 0; i < entries.size(); i++) {
                Entry entry = entries.get(i);
                File folder = outputDirectory;
                List<String> parts = new ArrayList<>();
                int current = entry.directory;
                while (current != 0) {
                    if (parts.size() >= 64 || current >= count || names[current] == null) {
                        throw new IOException("profundidad de carpetas no válida");
                    }
                    parts.add(names[current]);
                    current = parents[current];
                }
                for (int part = parts.size() - 1; part >= 0; part--) {
                    folder = new File(folder, parts.get(part));
                }
                File destination = new File(folder, entry.name);
                if (!paths.add(destination.getPath())) {
                    throw new IOException("archivo duplicado en la ROM");
                }
                long size = ends[entry.id] - starts[entry.id];
                totalBytes += size;
                if (totalBytes > MAX_EXTRACTED_SIZE) {
                    throw new IOException("los archivos de la ROM exceden el límite de tamaño");
                }
                if (!folder.isDirectory() && !folder.mkdirs()) {
                    throw new IOException("no se pudo crear una carpeta del juego");
                }
                rom.seek(starts[entry.id]);
                try (FileOutputStream output = new FileOutputStream(destination)) {
                    long remaining = size;
                    while (remaining > 0) {
                        int amount = (int) Math.min(buffer.length, remaining);
                        rom.readFully(buffer, 0, amount);
                        output.write(buffer, 0, amount);
                        remaining -= amount;
                    }
                }
                if (progress != null && (i % 64 == 0 || i + 1 == entries.size())) {
                    progress.onFiles(i + 1, entries.size());
                }
            }
            return entries.size();
        }
    }

    private static String safeName(byte[] bytes) throws IOException {
        for (byte value : bytes) {
            int c = value & 0xff;
            if (c < 0x20 || c > 0x7e || c == '/' || c == '\\' || c == ':') {
                throw new IOException("nombre de archivo no válido en la ROM");
            }
        }
        String name = new String(bytes, StandardCharsets.US_ASCII);
        if (".".equals(name) || "..".equals(name)) {
            throw new IOException("ruta no válida en la ROM");
        }
        return name;
    }

    private static void checkRegion(long offset, long size, long total) throws IOException {
        if (offset < 0x200 || size <= 0 || offset > total || size > total - offset) {
            throw new IOException("tabla fuera de la ROM");
        }
    }

    private static long u32(byte[] bytes, int offset) {
        return ((long) bytes[offset] & 0xff)
                | (((long) bytes[offset + 1] & 0xff) << 8)
                | (((long) bytes[offset + 2] & 0xff) << 16)
                | (((long) bytes[offset + 3] & 0xff) << 24);
    }

    private static int readU16(RandomAccessFile file) throws IOException {
        return file.readUnsignedByte() | (file.readUnsignedByte() << 8);
    }

    private static long readU32(RandomAccessFile file) throws IOException {
        return (long) readU16(file) | ((long) readU16(file) << 16);
    }
}
