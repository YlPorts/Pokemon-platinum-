# Pokémon Platinum Android 0.3.0

Port nativo basado en `pokeplatinum-pcport-source.zip` proporcionado por el usuario.
Aplicación: `org.pokeplatinum.android`. ABI de distribución: `arm64-v8a`.
Android mínimo: 7.0 (API 24). Requiere OpenGL ES 3.

## Reparaciones de la base

- `u32`, `s32` y `fx32` mantienen 32 bits en Android LP64. Los punteros siguen
  teniendo 64 bits. Hay comprobaciones de tamaños durante la compilación.
- Los heaps de Nitro alinean sus metadatos a 8 bytes en Android. Las reservas de
  sonido conservan su alineación a 32 bytes y sus callbacks de liberación.
- Se conserva el puntero completo de archivo/banco/reproductor en los callbacks.
- La apertura del SDAT inicializa el archivo una sola vez; valida tamaños de
  cabecera y tabla antes de leer/convertir. INFO y FAT usan el heap original.
- Se restaura la carga original de nombres de cajas del archivo de mensajes.
- El audio empieza al finalizar su inicialización; se corrigen la selección de
  canales, la salida estéreo y las transiciones a silencio.
- El menú está adaptado al tacto, hay opciones de pantalla en el inicio y el
  juego corre en un proceso separado para poder reiniciarlo después de un cierre.
- El diagnóstico copia la traza de inicio y la información de salida de Android.
- El runtime C++ se incluye en el APK. Bibliotecas preparadas para páginas de 16 KB.

## Compilar este paquete preparado

Los cambios ya están aplicados en este ZIP: **no ejecutar de nuevo los parches**.
Instalar JDK 17, Gradle 8.9, Android SDK 35, Build Tools 35.0.0 y NDK 27.2.12479018.
En Linux se necesitan Meson >= 1.12, Ninja, CMake, GCC, g++, nasm,
gcc-arm-none-eabi, binutils-arm-none-eabi, libpng-dev, libsdl2-dev y libenet-dev.

```sh
export ANDROID_SDK_ROOT=/ruta/al/android-sdk
export ANDROID_NDK_HOME="$ANDROID_SDK_ROOT/ndk/27.2.12479018"
gradle -p android assembleDebug
```

Resultado: `android/app/build/outputs/apk/debug/app-debug.apk`.
El APK generado por Gradle usa firma de depuración. El APK entregado en el chat
se firma posteriormente con la clave conservada para futuras versiones; esa
clave privada no se publica en el repositorio.

## Comprobaciones

`android-port-repair/tests/run_native_tests.sh .` ejecuta código real de los heaps,
el cargador SDAT y los reproductores con AddressSanitizer/UndefinedBehaviorSanitizer.
Las operaciones de dispositivo/sistema operativo están sustituidas en esta prueba.
Si están instalados GCC ARM64 y qemu-aarch64, también se ejecuta una versión ARM64.

`python3 android-port-repair/tests/check_gles.py .` compila/enlaza los shaders 2D y 3D
en un contexto OpenGL ES 3 de Mesa. Requiere libEGL y Mesa.

GitHub Actions incluye además un arranque en emulador Android x86_64. Su resultado
y captura se guardan en `Android-smoke-results`. Esto no sustituye las pruebas de
audio, GPU y rendimiento en un teléfono físico ARM64.

La selección de ROM sigue usando un archivo `.nds` de Pokémon Platinum USA.
