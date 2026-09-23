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

    candidates = [
        path for path in SOURCE_DIR.rglob("android/build.gradle")
        if (path.parent.parent / "meson.build").is_file()
    ]
    if len(candidates) != 1:
        roots = [str(path.relative_to(SOURCE_DIR)) for path in SOURCE_DIR.iterdir()]
        print(f"No se encontró un proyecto Android único. Raíz del ZIP: {roots[:20]}", file=sys.stderr)
        print(f"Candidatos: {candidates[:20]}", file=sys.stderr)
        return 1
    project = candidates[0]
    canonical_root = SOURCE_DIR / "pokeplatinum-pcport-source"
    if project.parent.parent != canonical_root:
        if canonical_root.exists():
            print(f"Destino ocupado: {canonical_root}", file=sys.stderr)
            return 1
        shutil.move(str(project.parent.parent), str(canonical_root))
        project = canonical_root / "android" / "build.gradle"
    print(f"Código reconstruido en {project.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
