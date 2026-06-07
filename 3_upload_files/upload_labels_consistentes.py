#!/usr/bin/env python3
"""
Sube los labels que corresponden exactamente a las imágenes
que ya están en Drive (images/train), sin importar cuántas
se alcanzaron a subir antes de la interrupción.

Flujo:
  1. Lista imágenes en Drive  → sabe exactamente qué subió
  2. Convierte .jpg/.png → .txt para obtener nombre de label
  3. Verifica existencia local de cada label
  4. Sube solo los labels encontrados
"""

import subprocess
import os
import tempfile
from datetime import datetime

SOURCE_LABELS = "/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED/labels/train"
DEST_LABELS   = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED/labels/train"
DRIVE_IMAGES  = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED/images/train"


def list_drive_images():
    print("\n[1/3] Listando imágenes ya subidas en Drive...")
    print("      Ruta Drive  : " + DRIVE_IMAGES)
    print("      Esto puede tardar varios minutos — espera...\n")

    proc = subprocess.Popen(
        ["rclone", "lsf", "--fast-list", DRIVE_IMAGES],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    files = []
    for line in proc.stdout:
        name = line.strip()
        if name:
            files.append(name)
            if len(files) % 5000 == 0:
                print(f"  ... {len(files):,} imágenes leídas de Drive hasta ahora", flush=True)

    proc.wait()
    if proc.returncode != 0:
        print(f"  ✗ Error: {proc.stderr.read().strip()}")
        return []

    print(f"  ✓ Total imágenes en Drive: {len(files):,}")
    return files


def to_label_name(image_name):
    return os.path.splitext(image_name)[0] + ".txt"


def resolve_labels(image_names):
    print("\n[2/3] Verificando labels locales correspondientes...")
    print(f"      Ruta local : {SOURCE_LABELS}\n")

    # Escanear el directorio UNA sola vez y cargar nombres en memoria
    print("      Leyendo directorio local una sola vez...", flush=True)
    local_labels = set()
    with os.scandir(SOURCE_LABELS) as it:
        for entry in it:
            if entry.is_file():
                local_labels.add(entry.name)
                if len(local_labels) % 10000 == 0:
                    print(f"      ... {len(local_labels):,} labels leídos localmente", flush=True)
    print(f"      ✓ {len(local_labels):,} labels en disco cargados en memoria\n")

    # Ahora la verificación es en memoria — instantánea
    found, missing = [], []
    total = len(image_names)

    for i, img in enumerate(image_names, 1):
        label = to_label_name(img)
        if label in local_labels:
            found.append(label)
        else:
            missing.append(label)

        if i % 5000 == 0 or i == total:
            pct = i / total * 100
            print(f"  ... {i:,}/{total:,} verificados ({pct:.1f}%) — "
                  f"encontrados: {len(found):,}  sin label: {len(missing):,}", flush=True)

    print(f"\n  ✓ Labels encontrados localmente : {len(found):,}")
    if missing:
        print(f"  ⚠ Sin archivo local (sin label) : {len(missing):,}  → se omiten")

    # Guardar reporte de faltantes por si se necesita revisar
    if missing:
        report_path = os.path.expanduser("~/rclone_logs/labels_sin_archivo.txt")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write("\n".join(missing))
        print(f"  → Lista de faltantes guardada en: {report_path}")

    return found


def upload_labels(label_names):
    print(f"\n[3/3] Subiendo {len(label_names):,} labels a Drive...")
    print("      El progreso se actualiza cada 5 segundos\n")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(label_names) + "\n")
        temp_path = f.name

    try:
        result = subprocess.run(
            [
                "rclone", "copy",
                "--files-from", temp_path,
                "--no-traverse",
                "--transfers", "8",
                "--drive-chunk-size", "64M",
                "--drive-pacer-burst", "200",
                "--drive-pacer-min-sleep", "0",
                "--stats", "5s",
                "--stats-one-line",
                "--progress",
                SOURCE_LABELS,
                DEST_LABELS,
            ]
        )
        if result.returncode != 0:
            print(f"\n  ✗ rclone terminó con error (código {result.returncode})")
            return False
        return True
    finally:
        os.unlink(temp_path)


def main():
    print("=" * 58)
    print("  SUBIDA DE LABELS CONSISTENTES CON IMÁGENES EN DRIVE")
    print(f"  Inicio : {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Labels : {SOURCE_LABELS}")
    print(f"  Destino: {DEST_LABELS}")
    print("=" * 58)

    images = list_drive_images()
    if not images:
        print("\nNo hay imágenes en Drive. Verifica la ruta y vuelve a intentar.")
        return

    labels_to_upload = resolve_labels(images)
    if not labels_to_upload:
        print("\nNo se encontraron labels locales para subir.")
        return

    ok = upload_labels(labels_to_upload)

    print(f"\n{'='*58}")
    if ok:
        print(f"  ✓ SUBIDA EXITOSA — {len(labels_to_upload):,} labels")
        print(f"  Destino: {DEST_LABELS}")
        print(f"\nPróximo paso: re-dividir imágenes+labels en train/val/test")
    else:
        print(f"  ✗ La subida falló — revisa los mensajes de error arriba")
    print(f"  Fin: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 58)


if __name__ == "__main__":
    main()
