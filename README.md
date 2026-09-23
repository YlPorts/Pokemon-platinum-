# Pokémon Platinum para Android

Este repositorio contiene el código fuente Android del port de Pokémon Platinum para PC. El archivo de código completo está guardado en fragmentos dentro de `.source-bundle/`; el flujo de GitHub Actions los reconstruye y compila el APK en cada subida a `main`.

## Compilar y descargar el APK

1. Abre **Actions → Android APK**.
2. Entra al último flujo terminado y descarga el artefacto `Pokemon-Platinum-Android-debug`.

También puedes ejecutar el flujo con **Run workflow**. El APK es de depuración y solo compila para `arm64-v8a`.

## Recuperar el código fuente

Con Python 3 instalado, ejecuta desde la raíz del repositorio:

```sh
python3 assemble-source-bundle.py
```

El script reconstruye y extrae el archivo completo en `_source/pokeplatinum-pcport-source/`.

## Archivos del juego

El APK no incluye una ROM ni los archivos extraídos. Al abrir la aplicación, importa la carpeta `root` de los archivos extraídos de tu propia copia estadounidense de Pokémon Platinum.
