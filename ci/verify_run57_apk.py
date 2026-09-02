#!/usr/bin/env python3
import hashlib
import sys
import zipfile
from pathlib import Path

EXPECTED = {
    "res/font/iransans_fanum_regular.ttf": "1df818a6b400da053448a007729d548436e76bdee48d52647bc2ed69a6ff62f9",
    "res/font/iransans_fanum_medium.ttf": "d8ab70132d0e59cd873a1fa212a6ae8b2867495a013fa55484615c360ce74cc0",
    "res/font/iransans_fanum_bold.ttf": "96d8e88e864c66c15447f27429711f6c3e5d14c5d9d633edd2bf6c22f870dd19",
}
DEJAVU_PLACEHOLDER = "ae7b7855e115a5966d8b1b3f80f254ccc117ec86f9965e202ee2940453837280"


def main() -> None:
    apk = Path(sys.argv[1])
    if not apk.is_file():
        raise SystemExit(f"APK not found: {apk}")

    with zipfile.ZipFile(apk) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise SystemExit(f"APK ZIP integrity failed at {corrupt}")

        embedded = set(archive.namelist())
        for name, expected_hash in EXPECTED.items():
            if name not in embedded:
                raise SystemExit(f"Required font missing from APK: {name}")
            actual_hash = hashlib.sha256(archive.read(name)).hexdigest()
            if actual_hash == DEJAVU_PLACEHOLDER:
                raise SystemExit(f"DejaVu placeholder detected: {name}")
            if actual_hash != expected_hash:
                raise SystemExit(
                    f"Unapproved font bytes for {name}: {actual_hash} != {expected_hash}"
                )

        unexpected_fonts = sorted(
            name for name in embedded
            if name.startswith("res/font/")
            and name.endswith((".ttf", ".otf"))
            and name not in EXPECTED
        )
        if unexpected_fonts:
            raise SystemExit(f"Unexpected embedded font binaries: {unexpected_fonts}")

    print("APK ZIP integrity and all three approved IRANSans FaNum hashes verified.")


if __name__ == "__main__":
    main()
