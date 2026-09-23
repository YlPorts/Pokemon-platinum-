package org.pokeplatinum.android;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.TextView;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class LauncherActivity extends Activity {
    private static final int REQUEST_IMPORT_ROM = 42;
    private static final String IMPORT_MARKER = ".root_imported";
    private static final String ASSET_VERSION_MARKER = ".android_assets_v027";
    private static final String SOUND_ASSET = "data/sound/pl_sound_data.sdat";
    private static final String SOUND_SHA256 = "2800b19d4936b52b5eb8a096c55a80142cab1c4a86988a9911fbc8b183dd5d19";
    private static final long MAX_ROM_BYTES = 512L * 1024 * 1024;

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private TextView status;
    private Button importButton;
    private Button playButton;
    private File gameDir;
    private boolean bundledAssetsReady;
    private boolean returnedFromGame;
    private Spinner layoutChoice;
    private Spinner fpsChoice;
    private Spinner scaleChoice;
    private Spinner syncChoice;
    private Spinner wideChoice;
    private android.widget.CheckBox swapChoice;
    private static final String[] LAYOUT_VALUES = {"vertical", "horizontal", "widescreen", "large"};
    private static final String[] FPS_VALUES = {"30", "60", "90", "120", "0"};

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        gameDir = new File(getFilesDir(), "game");
        buildScreen();
        setBusy(true, "Preparando los archivos incluidos…");
        worker.execute(() -> {
            String error = "";
            try {
                installBundledAssets();
            } catch (IOException exception) {
                error = "No se pudieron preparar los archivos: " + exception.getMessage();
            }
            final String message = error;
            runOnUiThread(() -> {
                bundledAssetsReady = message.isEmpty();
                if (bundledAssetsReady) {
                    updateReadyState();
                } else {
                    setBusy(false, message);
                }
            });
        });
    }

    private void buildScreen() {
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(padding, padding, padding, padding);

        TextView title = new TextView(this);
        title.setText("Pokémon Platinum para Android");
        title.setTextSize(24);
        content.addView(title);

        TextView instructions = new TextView(this);
        instructions.setText("Selecciona tu ROM de Pokémon Platinum USA (.nds). La aplicación extraerá automáticamente los archivos necesarios.");
        instructions.setTextSize(16);
        LinearLayout.LayoutParams instructionsParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        instructionsParams.topMargin = padding / 2;
        content.addView(instructions, instructionsParams);

        importButton = new Button(this);
        importButton.setText("Importar ROM (.nds)");
        importButton.setOnClickListener(view -> chooseRom());
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        buttonParams.topMargin = padding;
        content.addView(importButton, buttonParams);

        playButton = new Button(this);
        playButton.setText("Iniciar juego");
        playButton.setEnabled(false);
        playButton.setOnClickListener(view -> launchGame());
        content.addView(playButton, buttonParams);

        TextView options = new TextView(this);
        options.setText("Opciones de pantalla y rendimiento");
        options.setTextSize(19);
        content.addView(options, buttonParams);

        layoutChoice = addChoice(content, "Pantallas", new String[]{
                "Dos verticales", "Dos horizontales", "Principal panorámica", "Principal grande + secundaria"
        }, getSharedPreferences("display_options", MODE_PRIVATE).getInt("layout", 0));
        fpsChoice = addChoice(content, "Límite de FPS", new String[]{
                "30", "60", "90", "120", "Sin límite"
        }, getSharedPreferences("display_options", MODE_PRIVATE).getInt("fps", 1));
        scaleChoice = addChoice(content, "Resolución interna 3D", new String[]{
                "1× (rápida)", "2× (recomendada)", "3×", "4×"
        }, getSharedPreferences("display_options", MODE_PRIVATE).getInt("scale", 1));
        syncChoice = addChoice(content, "Sincronización vertical", new String[]{
                "Activada", "Desactivada"
        }, getSharedPreferences("display_options", MODE_PRIVATE).getInt("sync", 0));
        wideChoice = addChoice(content, "Expansión 3D panorámica", new String[]{
                "Automática", "Siempre activa", "Desactivada"
        }, getSharedPreferences("display_options", MODE_PRIVATE).getInt("wide", 0));
        swapChoice = new android.widget.CheckBox(this);
        swapChoice.setText("Intercambiar pantallas");
        swapChoice.setChecked(getSharedPreferences("display_options", MODE_PRIVATE).getBoolean("swap", false));
        content.addView(swapChoice);

        Button diagnostics = new Button(this);
        diagnostics.setText("Copiar diagnóstico");
        diagnostics.setOnClickListener(view -> copyDiagnostics());
        content.addView(diagnostics, buttonParams);

        status = new TextView(this);
        status.setTextSize(14);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        statusParams.topMargin = padding / 2;
        content.addView(status, statusParams);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        setContentView(scroll);
    }

    private Spinner addChoice(LinearLayout parent, String label, String[] values, int initial) {
        TextView caption = new TextView(this);
        caption.setText(label);
        caption.setTextSize(15);
        parent.addView(caption);
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, values);
        spinner.setAdapter(adapter);
        spinner.setSelection(Math.max(0, Math.min(initial, values.length - 1)));
        parent.addView(spinner);
        return spinner;
    }

    private void launchGame() {
        try {
            saveOptions();
            getSharedPreferences("display_options", MODE_PRIVATE).edit()
                    .putInt("layout", layoutChoice.getSelectedItemPosition())
                    .putInt("fps", fpsChoice.getSelectedItemPosition())
                    .putInt("scale", scaleChoice.getSelectedItemPosition())
                    .putInt("wide", wideChoice.getSelectedItemPosition())
                    .putBoolean("swap", swapChoice.isChecked())
                    .putInt("sync", syncChoice.getSelectedItemPosition()).apply();
            returnedFromGame = true;
            startActivity(new Intent(this, GameActivity.class));
        } catch (IOException exception) {
            status.setText("No se pudieron guardar las opciones: " + exception.getMessage());
        }
    }

    private void saveOptions() throws IOException {
        Map<String, String> values = new LinkedHashMap<>();
        values.put("ScreenLayout", LAYOUT_VALUES[layoutChoice.getSelectedItemPosition()]);
        values.put("InternalResolutionScale", String.valueOf(scaleChoice.getSelectedItemPosition() + 1));
        values.put("WindowWidth", "0");
        values.put("WindowHeight", "0");
        values.put("WidescreenMode", String.valueOf(wideChoice.getSelectedItemPosition()));
        values.put("SwapScreens", swapChoice.isChecked() ? "true" : "false");
        values.put("VsyncInterval", syncChoice.getSelectedItemPosition() == 0 ? "1" : "0");
        int fpsIndex = fpsChoice.getSelectedItemPosition();
        values.put("CapFrameRate", fpsIndex == 4 ? "false" : "true");
        values.put("TargetFPS", FPS_VALUES[fpsIndex == 4 ? 1 : fpsIndex]);

        File config = new File(gameDir, "sim_config.ini");
        String previous = "";
        if (config.isFile()) {
            try (InputStream input = new java.io.FileInputStream(config);
                 ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                copy(input, buffer);
                previous = buffer.toString("UTF-8");
            }
        }
        StringBuilder merged = new StringBuilder();
        boolean inGeneral = false;
        for (String line : previous.split("\\r?\\n")) {
            String trimmed = line.trim();
            if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
                inGeneral = "[General]".equalsIgnoreCase(trimmed);
            }
            int equals = line.indexOf('=');
            if (inGeneral && equals > 0 && values.containsKey(line.substring(0, equals).trim())) {
                continue;
            }
            if (!line.isEmpty()) merged.append(line).append('\n');
        }
        if (merged.indexOf("[General]") < 0) merged.insert(0, "[General]\n");
        int generalEnd = merged.indexOf("\n", merged.indexOf("[General]")) + 1;
        StringBuilder overrides = new StringBuilder();
        for (Map.Entry<String, String> entry : values.entrySet()) {
            overrides.append(entry.getKey()).append('=').append(entry.getValue()).append('\n');
        }
        merged.insert(generalEnd, overrides);
        File temporary = new File(gameDir, "sim_config.ini.new");
        try (OutputStream output = new FileOutputStream(temporary)) {
            output.write(merged.toString().getBytes(StandardCharsets.UTF_8));
        }
        if (config.exists() && !config.delete()) throw new IOException("configuración anterior bloqueada");
        if (!temporary.renameTo(config)) throw new IOException("no se pudo activar la configuración");
    }

    private void setBusy(boolean busy, String message) {
        status.setText(message);
        importButton.setEnabled(!busy && bundledAssetsReady);
        playButton.setEnabled(!busy && bundledAssetsReady && new File(gameDir, IMPORT_MARKER).isFile());
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (returnedFromGame && bundledAssetsReady) updateReadyState();
    }

    private void updateReadyState() {
        boolean imported = new File(gameDir, IMPORT_MARKER).isFile();
        String message = imported
                ? "ROM importada. Pulsa Iniciar juego."
                : "Selecciona tu archivo Pokémon Platinum USA (.nds).";
        File startup = new File(gameDir, "android_startup.txt");
        if (imported && startup.isFile()) {
            try (InputStream input = new java.io.FileInputStream(startup);
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                copy(input, output);
                message += "\nÚltima etapa de inicio: " + output.toString("UTF-8").trim();
            } catch (IOException ignored) {
                // Startup diagnostics are optional.
            }
        }
        status.setText(message);
        importButton.setEnabled(true);
        playButton.setEnabled(imported);
    }

    private void copyDiagnostics() {
        worker.execute(() -> {
            StringBuilder report = new StringBuilder("PLATINUM ANDROID 0.3.0\n");
            report.append(android.os.Build.MANUFACTURER).append(' ')
                    .append(android.os.Build.MODEL).append(" · Android ")
                    .append(android.os.Build.VERSION.RELEASE).append('\n');
            for (String name : new String[]{"android_startup.txt", "android_startup.log", "android_runtime.log", "sim_config.ini"}) {
                File file = new File(gameDir, name);
                if (!file.isFile()) continue;
                try (InputStream input = new FileInputStream(file)) {
                    report.append('\n').append(name).append(":\n")
                            .append(readDiagnosticText(input, 65536));
                } catch (IOException error) { report.append(error.getMessage()).append('\n'); }
            }
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                android.app.ActivityManager manager = (android.app.ActivityManager) getSystemService(ACTIVITY_SERVICE);
                for (android.app.ApplicationExitInfo exit : manager.getHistoricalProcessExitReasons(getPackageName(), 0, 8)) {
                    if (!exit.getProcessName().endsWith(":game")) continue;
                    report.append("\nSalida: ").append(exit.getReason()).append(" estado: ")
                            .append(exit.getStatus()).append("\n").append(exit.getDescription()).append('\n');
                    try (InputStream trace = exit.getTraceInputStream()) {
                        if (trace != null) {
                            byte[] bytes = readDiagnosticBytes(trace, 131072);
                            if (exit.getReason() == android.app.ApplicationExitInfo.REASON_CRASH_NATIVE) {
                                report.append("Tombstone protobuf (base64):\n")
                                        .append(android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP));
                            } else {
                                report.append(new String(bytes, StandardCharsets.UTF_8));
                            }
                        }
                    } catch (IOException error) { report.append(error.getMessage()); }
                    break;
                }
            }
            final String text = report.toString();
            runOnUiThread(() -> {
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Platinum diagnóstico", text));
                android.widget.Toast.makeText(this, "Diagnóstico copiado", android.widget.Toast.LENGTH_SHORT).show();
            });
        });
    }

    private static String readDiagnosticText(InputStream input, int limit) throws IOException {
        return new String(readDiagnosticBytes(input, limit), StandardCharsets.UTF_8);
    }

    private static byte[] readDiagnosticBytes(InputStream input, int limit) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int count;
        while (output.size() < limit && (count = input.read(chunk, 0, Math.min(chunk.length, limit - output.size()))) > 0) {
            output.write(chunk, 0, count);
        }
        return output.toByteArray();
    }

    private void chooseRom() {
        Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        picker.addCategory(Intent.CATEGORY_OPENABLE);
        picker.setType("*/*");
        picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivityForResult(picker, REQUEST_IMPORT_ROM);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_IMPORT_ROM || resultCode != RESULT_OK || data == null
                || data.getData() == null) {
            return;
        }
        Uri romUri = data.getData();
        setBusy(true, "Copiando ROM…");
        worker.execute(() -> {
            File temporaryRom = new File(getCacheDir(), "selected-game.nds");
            File staging = new File(getFilesDir(), "rom-import-staging");
            String error = "";
            try {
                deleteTree(staging);
                copySelectedRom(romUri, temporaryRom);
                runOnUiThread(() -> setBusy(true, "Extrayendo archivos de la ROM…"));
                NdsRomExtractor.extract(temporaryRom, staging, (done, total) -> {
                    if (done % 256 == 1 || done == total) {
                        int percent = (int) (100L * done / total);
                        runOnUiThread(() -> setBusy(true, "Extrayendo ROM: " + percent + "%"));
                    }
                });
                runOnUiThread(() -> setBusy(true, "Instalando archivos del juego…"));
                File marker = new File(gameDir, IMPORT_MARKER);
                if (marker.exists() && !marker.delete()) {
                    throw new IOException("no se pudo actualizar la importación anterior");
                }
                mergeFiles(staging, gameDir, "");
                restoreRuntimeHeader();
                if (!marker.createNewFile() && !marker.isFile()) {
                    throw new IOException("no se pudo finalizar la importación");
                }
            } catch (Exception exception) {
                error = "No se pudo importar la ROM: " + exception.getMessage();
            } finally {
                temporaryRom.delete();
                try {
                    deleteTree(staging);
                } catch (IOException ignored) {
                    // The next import clears a remaining staging directory.
                }
            }
            final String message = error;
            runOnUiThread(() -> {
                if (message.isEmpty()) {
                    updateReadyState();
                } else {
                    setBusy(false, message);
                }
            });
        });
    }

    private void copySelectedRom(Uri uri, File destination) throws IOException {
        try (InputStream input = getContentResolver().openInputStream(uri);
             OutputStream output = new FileOutputStream(destination)) {
            if (input == null) {
                throw new IOException("no se pudo abrir el archivo seleccionado");
            }
            byte[] buffer = new byte[64 * 1024];
            long copied = 0;
            int count;
            while ((count = input.read(buffer)) != -1) {
                copied += count;
                if (copied > MAX_ROM_BYTES) {
                    throw new IOException("la ROM supera el límite de 512 MB");
                }
                output.write(buffer, 0, count);
            }
        }
    }

    private void mergeFiles(File source, File destination, String assetPath) throws IOException {
        if (source.isDirectory()) {
            if (!destination.isDirectory() && !destination.mkdirs()) {
                throw new IOException("no se pudo crear " + destination.getName());
            }
            File[] children = source.listFiles();
            if (children == null) {
                throw new IOException("no se pudo leer la carpeta extraída");
            }
            for (File child : children) {
                String childPath = assetPath.isEmpty() ? child.getName() : assetPath + "/" + child.getName();
                mergeFiles(child, new File(destination, child.getName()), childPath);
            }
        } else {
            // Generated PC-port assets may differ from the retail NitroFS files.
            // Keep the built version when a ROM contains the same path.
            try (InputStream bundled = getAssets().open(assetPath)) {
                return;
            } catch (FileNotFoundException missing) {
                // This file only exists in the imported ROM.
            }
            if (destination.exists() && !destination.delete()) {
                throw new IOException("no se pudo reemplazar " + destination.getName());
            }
            if (!source.renameTo(destination)) {
                throw new IOException("no se pudo instalar " + destination.getName());
            }
        }
    }

    private static void deleteTree(File path) throws IOException {
        if (!path.exists()) {
            return;
        }
        if (path.isDirectory()) {
            File[] children = path.listFiles();
            if (children == null) {
                throw new IOException("no se pudo limpiar la extracción anterior");
            }
            for (File child : children) {
                deleteTree(child);
            }
        }
        if (!path.delete()) {
            throw new IOException("no se pudo limpiar " + path.getName());
        }
    }

    private void installBundledAssets() throws IOException {
        if (!gameDir.exists() && !gameDir.mkdirs()) {
            throw new IOException("no se pudo crear el directorio del juego");
        }
        File marker = new File(gameDir, ".android_assets_installed");
        File currentVersion = new File(gameDir, ASSET_VERSION_MARKER);
        if (marker.isFile() && currentVersion.isFile()) {
            ensureBundledSoundAsset();
            restoreRuntimeHeader();
            return;
        }
        // Upgrade old installs too: previous ROM imports replaced some
        // generated assets with incompatible retail versions.
        copyAssetDirectory("");
        ensureBundledSoundAsset();
        restoreRuntimeHeader();
        if (!marker.createNewFile() && !marker.isFile()) {
            throw new IOException("no se pudo registrar la instalación");
        }
        if (!currentVersion.createNewFile() && !currentVersion.isFile()) {
            throw new IOException("no se pudo registrar la actualización");
        }
    }

    private void ensureBundledSoundAsset() throws IOException {
        File sound = new File(gameDir, SOUND_ASSET);
        if (sound.isFile() && SOUND_SHA256.equals(sha256(sound))) {
            return;
        }

        File parent = sound.getParentFile();
        if (parent == null || (!parent.isDirectory() && !parent.mkdirs())) {
            throw new IOException("no se pudo preparar la carpeta de sonido");
        }
        File temporary = new File(parent, sound.getName() + ".new");
        try (InputStream input = getAssets().open(SOUND_ASSET);
             OutputStream output = new FileOutputStream(temporary)) {
            copy(input, output);
        }
        if (!SOUND_SHA256.equals(sha256(temporary))) {
            throw new IOException("el SDAT incluido está incompleto");
        }
        if (sound.exists() && !sound.delete()) {
            throw new IOException("no se pudo reemplazar el SDAT anterior");
        }
        if (!temporary.renameTo(sound)) {
            throw new IOException("no se pudo instalar el SDAT");
        }
    }

    private static String sha256(File file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = new FileInputStream(file)) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    digest.update(buffer, 0, count);
                }
            }
            StringBuilder hex = new StringBuilder(64);
            for (byte value : digest.digest()) {
                hex.append(Character.forDigit((value >>> 4) & 15, 16));
                hex.append(Character.forDigit(value & 15, 16));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IOException("SHA-256 no está disponible", error);
        }
    }

    private void restoreRuntimeHeader() throws IOException {
        File header = new File(gameDir, "header.bin");
        File temporary = new File(gameDir, "header.bin.new");
        try (InputStream input = getAssets().open("header.bin");
             OutputStream output = new FileOutputStream(temporary)) {
            copy(input, output);
        }
        if (header.exists() && !header.delete()) {
            throw new IOException("no se pudo reparar la cabecera del juego");
        }
        if (!temporary.renameTo(header)) {
            throw new IOException("no se pudo instalar la cabecera del juego");
        }
    }

    private void copyAssetDirectory(String assetPath) throws IOException {
        String[] children;
        try {
            children = getAssets().list(assetPath);
        } catch (IOException error) {
            children = new String[0];
        }
        if (children != null && children.length > 0) {
            for (String childName : children) {
                String childPath = assetPath.isEmpty() ? childName : assetPath + "/" + childName;
                copyAssetDirectory(childPath);
            }
            return;
        }
        if (assetPath.isEmpty()) {
            return;
        }
        File destination = new File(gameDir, assetPath);
        File parent = destination.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("no se pudo crear " + parent.getName());
        }
        try (InputStream input = getAssets().open(assetPath);
             OutputStream output = new FileOutputStream(destination)) {
            copy(input, output);
        } catch (FileNotFoundException directory) {
            if (!destination.exists() && !destination.mkdirs()) {
                throw new IOException("no se pudo crear " + destination.getName());
            }
        }
    }

    private static void copy(InputStream input, OutputStream output) throws IOException {
        byte[] buffer = new byte[64 * 1024];
        int count;
        while ((count = input.read(buffer)) != -1) {
            output.write(buffer, 0, count);
        }
    }

    @Override
    protected void onDestroy() {
        worker.shutdown();
        super.onDestroy();
    }
}
