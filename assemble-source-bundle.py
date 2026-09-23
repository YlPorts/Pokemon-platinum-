#!/usr/bin/env python3
"""Rebuild and extract the Android source archive uploaded in numbered parts."""

from pathlib import Path
import shutil
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
PREFIX = "pokeplatinum-android-source.zip.t0."
EXPECTED = [ROOT / f"{PREFIX}{number:03d}" for number in (1, 2, 3)]
SOURCE_DIR = ROOT / "_source"


def main() -> int:
    present = sorted(ROOT.glob(f"{PREFIX}*"))
    if present != EXPECTED:
        missing = [path.name for path in EXPECTED if path not in present]
        unexpected = [path.name for path in present if path not in EXPECTED]
        print(f"Fragmentos incompletos: faltan {missing}; inesperados {unexpected}", file=sys.stderr)
        return 1

    archive_path = ROOT / "_source.zip"
    with archive_path.open("wb") as archive:
        for part in EXPECTED:
            with part.open("rb") as fragment:
                shutil.copyfileobj(fragment, archive)

    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Archivo corrupto: {bad}")
            target = SOURCE_DIR.resolve()
            for member in archive.infolist():
                destination = (target / member.filename).resolve()
                if not destination.is_relative_to(target):
                    raise ValueError(f"Ruta insegura en ZIP: {member.filename}")
            archive.extractall(SOURCE_DIR)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"No se pudo reconstruir el código: {error}", file=sys.stderr)
        return 1
    finally:
        archive_path.unlink(missing_ok=True)

    project = SOURCE_DIR / "pokeplatinum-pcport-source" / "android" / "build.gradle"
    if not project.is_file():
        print("El ZIP no contiene el proyecto Android esperado.", file=sys.stderr)
        return 1
    print(f"Código reconstruido en {project.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
