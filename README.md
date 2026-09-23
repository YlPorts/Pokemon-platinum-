# Pokémon Platinum para Android

El proyecto Android está dividido en tres fragmentos del mismo ZIP:

- `pokeplatinum-android-source.zip.t0.001`
- `pokeplatinum-android-source.zip.t0.002`
- `pokeplatinum-android-source.zip.t0.003`

**Estado actual:** falta el fragmento `.002`. Las partes `.001` y `.003` no forman un ZIP completo. Sube la parte `.002` correspondiente a esos mismos archivos; no mezcles fragmentos de otro ZIP.

Al subir la parte faltante, el flujo [Android APK](../../actions/workflows/android-apk.yml) se inicia automáticamente. También se puede iniciar manualmente desde **Actions → Android APK → Run workflow**. El flujo reconstruye el ZIP con `assemble-source-bundle.py`, intenta compilar el proyecto con Gradle y, si termina correctamente, publica el artefacto `Pokemon-Platinum-Android-debug`.

El APK de depuración, si la compilación termina, estará en `android/app/build/outputs/apk/debug/app-debug.apk` dentro del código reconstruido. Este flujo aún no ha producido un APK probado.

Para reconstruir el código localmente:

```sh
python3 assemble-source-bundle.py
```

El código queda en `_source/pokeplatinum-pcport-source/`. El APK no incluye una ROM ni los archivos del juego: la aplicación requiere importar la carpeta `root` extraída de una copia propia de Pokémon Platinum estadounidense.
