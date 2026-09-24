# Pokémon Platinum Android 0.3.5

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

## Pantallas y controles 0.3.1

- Adaptativa: dos pantallas verticales en retrato y horizontales en paisaje.
- Mundo exterior 3D: cámara panorámica real, interfaz 2D y pantalla táctil 4:3.
- Formato del dispositivo, 16:9 o 21:9; los menús y combates conservan ambas pantallas.
- Giro por sensor o bloqueo vertical/horizontal independiente del diseño.
- Cruceta DS con diagonales, X/Y/A/B en rombo, L/R, START/SELECT.
- Tamaño y opacidad configurables. R ya no oculta la pantalla táctil.
- MENU abre opciones; SWAP intercambia las pantallas; DS oculta/muestra la
  secundaria solo al explorar en horizontal. La pantalla vuelve en menús.
- Un dedo de control y otro de lápiz pueden funcionar simultáneamente.
- Misma firma que 0.3.0: instalar encima conservando ROM y partida.

## 0.3.2 — una pantalla y renderizador Android

Panorámica y Automática muestran una sola pantalla. En horizontal, los controles
flotan sobre toda la superficie; las escenas 4:3 se amplían y centran sin estirar.
En vertical se conserva una zona inferior para los dedos. Los otros tres modos
siguen mostrando ambas pantallas, a elección del usuario.

La selección sigue el motor principal de DS, con indicaciones explícitas para
la Pokéball y Sí/No de Rowan, el teclado y la selección de comandos, movimientos,
objetivos y Sí/No del combate. SWAP permite ver la otra pantalla y AUTO restablece
la selección. Un cambio de escena o pantalla solicitada cancela el cambio manual.
R sigue siendo el botón DS; en PC su atajo anterior alternaba la superposición
táctil al explorar, no era un selector automático completo. No se afirma cobertura
exhaustiva de todos los minijuegos: SWAP mantiene accesibles las dos pantallas.

En los dos puntos de dibujo 3D se enlaza el shader antes de enviar sus uniformes;
se eliminan las consultas GL_CURRENT_PROGRAM y enlaces redundantes por uniforme.
No se altera la velocidad de la simulación ni se promete un número de FPS.
La mejora en un teléfono físico necesita medición allí.

La caché de texturas 3D ya no se vacía entera al superar 1024 entradas. Retira
hasta 64 entradas antiguas por fotograma y conserva las usadas en los últimos
fotogramas, incluidas las referenciadas por el dibujo translúcido pendiente.


## 0.3.3 — optimización sin reducir la imagen

Se comparó el ZIP `pokeplatinum-pcport-windows-fixed.zip` con la base de Android.
El motor 3D de ese paquete apenas cambia; no se reemplazan las adaptaciones
GLES, ABI, memoria ni audio de Android por las implementaciones de Windows.
Se adapta su búsqueda alternativa de recursos españoles cuando falta la ruta
original, conservando la prioridad de los archivos existentes y de los mods.
El importador sigue requiriendo una ROM USA CPUE; esto no añade soporte completo
para ROM de otras regiones.

- En modo de una pantalla se evita componer por software el motor 2D invisible.
  La lógica del juego, los comandos 3D, el audio y VBlank siguen ejecutándose.
  Los modos de dos pantallas siguen dibujando ambas.
- Los lotes 3D se envían a zonas sucesivas del búfer de vértices. Al agotarlo se
  solicita almacenamiento nuevo, evitando sobrescribir datos todavía en uso.
  Se conserva el orden de dibujo, geometría, colores, texturas y transparencias.
- CRC32 procesa ocho bytes por iteración, con resultados idénticos al original.
  Se mantiene la comprobación de cambios de texturas y paletas animadas.
- Los rectángulos de presentación solo se vuelven a enviar cuando cambian.

No se reducen resolución, distancia de dibujo, efectos ni velocidad del juego.
Las pruebas comparan CRC, rutas de pantalla y 1402 envíos de vértices, además
de comparar píxeles con el shader GLES real, texturas, alfa, descarte y niebla.
La aceleración del CRC medida en el ordenador de compilación no representa
los FPS del teléfono. El rendimiento 3D necesita comprobarse en el dispositivo.


## 0.3.4 — reloj y velocidad de personajes

El limitador antiguo utilizaba TargetFPS tanto para la espera intermedia como
para la presentación. Elegir 30 reducía a la mitad las actualizaciones de campo;
además se añadía la espera de VSync después de la espera por software y se
reiniciaba el reloj al terminar. Esto podía retrasar movimiento y animaciones.

Android usa ahora plazos absolutos de VBlank a 60 Hz, compartidos por las dos
esperas. El campo conserva sus dos VBlank por actualización (30 por segundo).
El tiempo de presentación cuenta para el siguiente plazo. Los límites de FPS
solo limitan la presentación; no prometen interpolación ni nuevos fotogramas del
juego a 90/120. Los antiguos trucos de velocidad 60Fps/60FpsSpeedFix de PC se
ignoran en Android para conservar el ritmo original, incluso con ajustes previos.
Un regreso desde segundo plano o una pausa larga no provoca una ráfaga acelerada.

El shader 3D reutiliza uniformes idénticos, incluidos los parámetros de niebla;
los cambios se comparan byte por byte y se envían cuando corresponda. No se
modifican resolución, geometría, texturas, efectos ni orden de dibujo.

El diagnóstico registra cada cinco segundos VBlank/s, presentaciones/s, tiempo
de trabajo, espera del reloj y espera de intercambio. Sirve para distinguir
carga de CPU/GPU de retrasos del limitador; no son mediciones de GPU aisladas.
Pruebas de reloj: 20 combinaciones de límite/VSync, pausas breves, reanudación,
señales EINTR y límite de presentación a 30. Pruebas de uniformes: conservación
exacta de datos, cambios animados, reinicio y saturación de caché.

## Trabajo de CPU y diagnóstico 0.3.5

- Las listas de sprites por línea/prioridad se calculan una vez por composición.
  Mantienen el orden OAM, objetos afines/dobles, ventanas, recorte y envoltura Y.
  Se omite la conversión de líneas sin objetos. No se reduce resolución ni efectos.
- Texturas y paletas repetidas reutilizan su CRC únicamente después de comparar
  todos los bytes: las escrituras en VRAM dentro del mismo fotograma se detectan.
  Caché acotada (hasta 4 MiB entre datos de texturas y paletas).
- La línea de mosaico de OBJ deja de usar una variable sin inicializar. Esto no
  añade una implementación nueva del efecto mosaico.
- El proceso Android aislado termina después de vaciar stdio, sin ejecutar
  destructores globales mientras siguen activos los hilos de Nitro. Evita esa
  carrera de cierre; no demuestra el origen de todos los fallos FORTIFY.
- Registro de rendimiento independiente, cada dos segundos, con sesión, GPU,
  VBlank, FPS presentados, trabajo/espera/swap y composición 2D+interfaz.
  Se conserva entre arranques y rota al superar 64 KiB. El diagnóstico lee
  el final de los registros. FPS del menú mide presentaciones completas.
- Prueba diferencial con las funciones reales de OBJ (400 estados OAM
  aleatorios de ambas pantallas), ASan/UBSan y validación de cambios de VRAM.
  Las pruebas de emulador no equivalen a medir zonas 3D en el Samsung SM-A155M.
