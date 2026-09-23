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
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class LauncherActivity extends Activity {
    private static final int REQUEST_IMPORT_ROM = 42;
    private static final String IMPORT_MARKER = ".root_imported";
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
                ? "ROM importada. Ya puedes jugar."
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
                mergeFiles(staging, gameDir);
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

    private static void mergeFiles(File source, File destination) throws IOException {
        if (source.isDirectory()) {
            if (!destination.isDirectory() && !destination.mkdirs()) {
                throw new IOException("no se pudo crear " + destination.getName());
            }
            File[] children = source.listFiles();
            if (children == null) {
                throw new IOException("no se pudo leer la carpeta extraída");
            }
            for (File child : children) {
                mergeFiles(child, new File(destination, child.getName()));
            }
        } else {
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
        if (marker.isFile()) {
            restoreRuntimeHeader();
            return;
        }
        copyAssetDirectory("");
        restoreRuntimeHeader();
        if (!marker.createNewFile() && !marker.isFile()) {
            throw new IOException("no se pudo registrar la instalación");
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
