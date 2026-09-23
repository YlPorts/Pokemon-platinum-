package org.pokeplatinum.android;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;

public final class NdsRomExtractorTest {
    private static void put16(byte[] bytes, int offset, int value) {
        bytes[offset] = (byte) value;
        bytes[offset + 1] = (byte) (value >> 8);
    }

    private static void put32(byte[] bytes, int offset, int value) {
        put16(bytes, offset, value);
        put16(bytes, offset + 2, value >> 16);
    }

    private static byte[] fixture() {
        byte[] rom = new byte[0x405];
        System.arraycopy("POKEMON PL".getBytes(StandardCharsets.US_ASCII), 0, rom, 0, 10);
        System.arraycopy("CPUE".getBytes(StandardCharsets.US_ASCII), 0, rom, 0x0c, 4);
        put32(rom, 0x40, 0x200);
        put32(rom, 0x44, 0x26);
        put32(rom, 0x48, 0x300);
        put32(rom, 0x4c, 8);
        put32(rom, 0x200, 0x10);
        put16(rom, 0x204, 0);
        put16(rom, 0x206, 2);
        put32(rom, 0x208, 0x1c);
        put16(rom, 0x20c, 0);
        put16(rom, 0x20e, 0xf000);
        rom[0x210] = (byte) 0x88;
        System.arraycopy("resource".getBytes(StandardCharsets.US_ASCII), 0, rom, 0x211, 8);
        put16(rom, 0x219, 0xf001);
        rom[0x21c] = 8;
        System.arraycopy("test.bin".getBytes(StandardCharsets.US_ASCII), 0, rom, 0x21d, 8);
        put32(rom, 0x300, 0x400);
        put32(rom, 0x304, 0x405);
        System.arraycopy("HELLO".getBytes(StandardCharsets.US_ASCII), 0, rom, 0x400, 5);
        return rom;
    }

    private static void expectInvalid(File rom, File output) throws Exception {
        try {
            NdsRomExtractor.extract(rom, output, null);
            throw new AssertionError("Invalid ROM was accepted");
        } catch (IOException expected) {
            // Bad game codes and out-of-range file offsets must be rejected.
        }
    }

    public static void main(String[] args) throws Exception {
        File directory = Files.createTempDirectory("platinum-rom-test").toFile();
        File rom = new File(directory, "fixture.nds");
        byte[] valid = fixture();
        Files.write(rom.toPath(), valid);
        File output = new File(directory, "extracted");
        if (NdsRomExtractor.extract(rom, output, null) != 1
                || !Arrays.equals("HELLO".getBytes(StandardCharsets.US_ASCII),
                        Files.readAllBytes(new File(output, "resource/test.bin").toPath()))
                || Files.size(new File(output, "header.bin").toPath()) != 0x200) {
            throw new AssertionError("NitroFS extraction was incorrect");
        }
        byte[] wrongGame = valid.clone();
        wrongGame[0x0f] = 'S';
        Files.write(rom.toPath(), wrongGame);
        expectInvalid(rom, new File(directory, "wrong-game"));
        byte[] badFat = valid.clone();
        put32(badFat, 0x304, 0x500);
        Files.write(rom.toPath(), badFat);
        expectInvalid(rom, new File(directory, "bad-fat"));
        System.out.println("ROM extractor: valid files and invalid ROMs checked");
    }
}
