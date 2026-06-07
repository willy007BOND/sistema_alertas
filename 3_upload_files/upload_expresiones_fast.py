#!/usr/bin/env python3
"""
Sube YOLO_EXPRESIONES_UNIFIED a Google Drive con rclone.
Orden: test → val  (train al final si se descomenta)
Una llamada rclone por carpeta — sin micro-lotes.
"""
import subprocess
import sys
from datetime import datetime

SOURCE = "/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED"
DEST = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED"

FOLDERS = [
    "images/test",
    "labels/test",
    "images/val",
    "labels/val",
    # "images/train",
    # "labels/train",
]

LOG_FILE = "/tmp/rclone_expresiones.log"

RCLONE_FLAGS = [
    "--transfers", "8",
    "--drive-chunk-size", "32M",
    "--tpslimit", "6",
    "--stats", "15s",
    "--stats-log-level", "NOTICE",
    "--log-level", "NOTICE",
    "--log-file", LOG_FILE,
]


def upload_folder(subfolder: str, idx: int, total: int) -> bool:
    src = f"{SOURCE}/{subfolder}"
    dst = f"{DEST}/{subfolder}"
    tag = f"[{idx}/{total}] {subfolder}"

    print(f"\n{'='*55}")
    print(f"  {tag}")
    print(f"  Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")

    cmd = ["rclone", "copy"] + RCLONE_FLAGS + [src, dst]
    result = subprocess.run(cmd)

    ok = result.returncode == 0
    status = "OK" if ok else f"ERROR (código {result.returncode})"
    print(f"\n  {tag} → {status}  ({datetime.now().strftime('%H:%M:%S')})")
    return ok


def main():
    print("=" * 55)
    print("  SUBIDA EXPRESIONES → Google Drive")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    failures = []
    for i, folder in enumerate(FOLDERS, 1):
        ok = upload_folder(folder, i, len(FOLDERS))
        if not ok:
            failures.append(folder)

    print(f"\n{'='*55}")
    if failures:
        print(f"  TERMINADO CON ERRORES en: {', '.join(failures)}")
        sys.exit(1)
    else:
        print(f"  SUBIDA COMPLETA — {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 55)


if __name__ == "__main__":
    main()
