#!/usr/bin/env python3
"""Save the exact prepared source from CI, with no generated binaries/caches."""
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1])
excluded = {'.git', '.gradle', '__pycache__', 'build_android', 'build', 'jniLibs'}
with zipfile.ZipFile('Pokemon-Platinum-Android-v0.3.5-source.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in root.rglob('*'):
        relative = file.relative_to(root)
        if not file.is_file() or excluded.intersection(relative.parts):
            continue
        if file.name == 'gradle-wrapper.jar':
            continue
        if relative.parts[:2] == ('third_party', 'android'):
            continue
        archive.write(file, Path('pokeplatinum-android') / relative)
    for file in Path('android').rglob('*'):
        if file.is_file() and not '__pycache__' in file.parts:
            archive.write(file, Path('pokeplatinum-android/android-port-repair') / file.relative_to('android'))

    archive.write('android/PORT_ANDROID.md', 'pokeplatinum-android/ANDROID_NOTES.md')
