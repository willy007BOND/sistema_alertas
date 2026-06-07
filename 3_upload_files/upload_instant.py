#!/usr/bin/env python3
import os
import subprocess
import tempfile
from datetime import datetime

SOURCE = "/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED"
DEST = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED"
BATCH_SIZE = 20

FOLDERS = [
    "images/train",
    "images/val",
    "images/test",
    "labels/train",
    "labels/val",
    "labels/test"
]


def upload_batch(file_names, subfolder, batch_num, uploaded_so_far):
    src = os.path.join(SOURCE, subfolder)
    dst = f"{DEST}/{subfolder}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(file_names) + "\n")
        temp_path = f.name

    print(f"\n  --- Lote {batch_num}: subiendo {len(file_names)} archivos ---")
    try:
        subprocess.run(
            [
                "rclone", "copy",
                "--files-from", temp_path,
                "--no-traverse",
                "--transfers", "4",
                "--drive-chunk-size", "32M",
                "--progress",
                src, dst,
            ],
        )
        uploaded_so_far += len(file_names)
        print(f"  ✓ Lote {batch_num} completado — total subidos: {uploaded_so_far}")
        return uploaded_so_far
    finally:
        os.unlink(temp_path)


def process_folder(subfolder, folder_index, total_folders):
    src_path = os.path.join(SOURCE, subfolder)
    print(f"\n{'='*50}")
    print(f"[{folder_index}/{total_folders}] {subfolder}")
    print(f"{'='*50}")

    if not os.path.isdir(src_path):
        print(f"  Carpeta no encontrada, se omite.")
        return

    batch = []
    uploaded = 0
    batch_num = 0
    found = 0

    print("  Escaneando archivos...", flush=True)

    with os.scandir(src_path) as it:
        for entry in it:
            if entry.is_file():
                batch.append(entry.name)
                found += 1
                if found % 10 == 0:
                    print(f"  {found} archivos encontrados...", flush=True)

                if len(batch) >= BATCH_SIZE:
                    batch_num += 1
                    uploaded = upload_batch(batch, subfolder, batch_num, uploaded)
                    batch = []

    if batch:
        batch_num += 1
        uploaded = upload_batch(batch, subfolder, batch_num, uploaded)

    print(f"\n  Carpeta completada: {uploaded} archivos subidos")


def main():
    print("=" * 50)
    print(" SUBIDA A GOOGLE DRIVE")
    print(f" Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)

    for i, folder in enumerate(FOLDERS, 1):
        process_folder(folder, i, len(FOLDERS))

    print(f"\n{'='*50}")
    print(f" SUBIDA COMPLETA — {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
