#!/usr/bin/env python3
"""
Sube un lote de imagenes locales de train a Google Drive sin validacion previa.

No borra archivos en Drive. Genera un manifest local con los primeros N archivos
de imagen en images/train y lo entrega a rclone copy mediante --files-from.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

SOURCE_IMAGES = "/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED/images/train"
DEST_IMAGES = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED/images/train"
LOG_DIR = Path.home() / "rclone_logs"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_appledouble_name(name):
    return name.startswith("._") or "_._" in name


def wanted_stems_from_labels(label_manifest):
    if not label_manifest:
        return None

    stems = set()
    with open(label_manifest, "r", encoding="utf-8") as fh:
        for line in fh:
            name = line.strip()
            if name and not is_appledouble_name(name):
                stems.add(Path(name).stem)
    print(f"  Labels base para equivalencia: {len(stems):,}")
    return stems


def build_manifest(source_images, limit, label_manifest=None):
    print(f"\n[1/2] Creando manifest con hasta {limit:,} imagenes locales...")
    print(f"  Origen: {source_images}")
    wanted_stems = wanted_stems_from_labels(label_manifest)

    names = []
    with os.scandir(source_images) as entries:
        for entry in entries:
            name = entry.name
            if is_appledouble_name(name) or Path(name).suffix.lower() not in IMG_EXTS:
                continue
            if wanted_stems is not None and Path(name).stem not in wanted_stems:
                continue
            names.append(name)
            if len(names) % 1000 == 0:
                print(f"  ... {len(names):,} imagenes agregadas al manifest", flush=True)
            if len(names) >= limit:
                break
            if wanted_stems is not None and len(names) >= len(wanted_stems):
                break

    if not names:
        raise RuntimeError("No se encontraron imagenes locales para subir.")

    manifest = tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_train_images.txt",
        delete=False,
        encoding="utf-8",
    )
    with manifest:
        manifest.write("\n".join(names))
        manifest.write("\n")

    print(f"  OK: {len(names):,} imagenes en manifest")
    print(f"  Manifest temporal: {manifest.name}")
    return manifest.name, len(names)


def upload_manifest(manifest_path, source_images, dest_images, args):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "upload_train_images_lote.log"

    print(f"\n[2/2] Subiendo lote de imagenes a Drive...")
    print(f"  Destino: {dest_images}")
    print(f"  Log    : {log_file}")

    cmd = [
        "rclone",
        "copy",
        "--files-from",
        manifest_path,
        "--ignore-existing",
        "--no-traverse",
        "--transfers",
        str(args.transfers),
        "--checkers",
        str(args.checkers),
        "--drive-chunk-size",
        args.drive_chunk_size,
        "--tpslimit",
        str(args.tpslimit),
        "--stats",
        args.stats,
        "--stats-one-line",
        "--log-file",
        str(log_file),
        "--log-level",
        "INFO",
        "--progress",
        source_images,
        dest_images,
    ]

    return subprocess.run(cmd).returncode


def clean_names_from_manifest(manifest_path):
    names = []
    with open(manifest_path, "r", encoding="utf-8") as fh:
        for line in fh:
            name = line.strip()
            if not name or is_appledouble_name(name):
                continue
            names.append(name)
    return names


def write_block_manifest(names, start, end):
    path = Path(tempfile.gettempdir()) / f"train_images_equivalentes_{start}_{end}.txt"
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(names[start - 1:end]))
        fh.write("\n")
    return path


def start_rclone_block(manifest_path, source_images, dest_images, args, start, end):
    log_file = LOG_DIR / f"upload_train_images_{start}_{end}_no_repisar.log"
    cmd = [
        "rclone",
        "copy",
        "--files-from",
        str(manifest_path),
        "--ignore-existing",
        "--no-traverse",
        "--transfers",
        str(args.pipeline_transfers),
        "--checkers",
        str(args.pipeline_checkers),
        "--drive-chunk-size",
        args.drive_chunk_size,
        "--tpslimit",
        str(args.pipeline_tpslimit),
        "--stats",
        args.stats,
        "--stats-one-line",
        "--log-file",
        str(log_file),
        "--log-level",
        "INFO",
        "--progress",
        source_images,
        dest_images,
    ]
    print(f"  Lanzando bloque {start}-{end}: {manifest_path}", flush=True)
    return subprocess.Popen(cmd)


def upload_pipeline(args):
    if not args.from_label_manifest:
        raise RuntimeError("--pipeline requiere --from-label-manifest.")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print("\n[PIPELINE] Preparando manifest equivalente completo...")
    full_manifest, _ = build_manifest(args.source_images, args.limit, args.from_label_manifest)
    names = clean_names_from_manifest(full_manifest)
    print(f"[PIPELINE] Imagenes limpias disponibles: {len(names):,}")

    active = []
    next_start = 1
    completed = 0
    failed = 0

    try:
        while next_start <= len(names) or active:
            while next_start <= len(names) and len(active) < args.pipeline_lanes:
                end = min(next_start + args.pipeline_block_size - 1, len(names))
                block_manifest = write_block_manifest(names, next_start, end)
                proc = start_rclone_block(block_manifest, args.source_images, args.dest_images, args, next_start, end)
                active.append((proc, next_start, end))
                next_start = end + 1
                time.sleep(args.pipeline_stagger)

            still_active = []
            for proc, start, end in active:
                code = proc.poll()
                if code is None:
                    still_active.append((proc, start, end))
                elif code == 0:
                    completed += 1
                    print(f"  OK bloque {start}-{end}", flush=True)
                else:
                    failed += 1
                    print(f"  ERROR bloque {start}-{end}: rclone codigo {code}", flush=True)
            active = still_active

            print(
                f"[PIPELINE] activos={len(active)} completados={completed} "
                f"fallidos={failed} siguiente={next_start}",
                flush=True,
            )
            if active or next_start <= len(names):
                time.sleep(args.pipeline_poll)
    except KeyboardInterrupt:
        print("\n[PIPELINE] Interrumpido. Enviando Ctrl+C a carriles activos...")
        for proc, _, _ in active:
            proc.send_signal(2)
        raise

    return 0 if failed == 0 else 1


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sube un lote de imagenes train a Drive sin validacion previa."
    )
    parser.add_argument("--limit", type=int, default=15000, help="Cantidad maxima de imagenes a poner en el manifest.")
    parser.add_argument("--source-images", default=SOURCE_IMAGES)
    parser.add_argument("--dest-images", default=DEST_IMAGES)
    parser.add_argument(
        "--from-label-manifest",
        help="Manifest de labels .txt para subir solo imagenes equivalentes por nombre base.",
    )
    parser.add_argument("--transfers", type=int, default=4)
    parser.add_argument("--checkers", type=int, default=8)
    parser.add_argument("--drive-chunk-size", default="32M")
    parser.add_argument("--tpslimit", type=int, default=4)
    parser.add_argument("--stats", default="30s")
    parser.add_argument("--keep-manifest", action="store_true")
    parser.add_argument("--pipeline", action="store_true", help="Sube en bloques paralelos sin repisar.")
    parser.add_argument("--pipeline-lanes", type=int, default=5)
    parser.add_argument("--pipeline-block-size", type=int, default=500)
    parser.add_argument("--pipeline-transfers", type=int, default=2)
    parser.add_argument("--pipeline-checkers", type=int, default=4)
    parser.add_argument("--pipeline-tpslimit", type=int, default=2)
    parser.add_argument("--pipeline-stagger", type=int, default=30)
    parser.add_argument("--pipeline-poll", type=int, default=30)
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 66)
    print("  SUBIDA LOTE IMAGENES TRAIN SIN VALIDACION")
    print(f"  Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 66)

    if not os.path.isdir(args.source_images):
        print(f"ERROR: no existe la carpeta local: {args.source_images}")
        sys.exit(1)

    if args.pipeline:
        try:
            code = upload_pipeline(args)
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario.")
            sys.exit(130)
        except Exception as exc:
            print(f"\nERROR: {exc}")
            sys.exit(1)
        sys.exit(code)

    manifest_path = None
    try:
        manifest_path, total = build_manifest(args.source_images, args.limit, args.from_label_manifest)
        code = upload_manifest(manifest_path, args.source_images, args.dest_images, args)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
    finally:
        if manifest_path and not args.keep_manifest:
            try:
                os.unlink(manifest_path)
            except OSError:
                pass

    print(f"\n{'=' * 66}")
    if code == 0:
        print(f"  SUBIDA DE LOTE FINALIZADA: {total:,} imagenes procesadas por rclone")
    else:
        print(f"  rclone termino con codigo {code}. Revisa el log.")
        sys.exit(code)
    print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 66)


if __name__ == "__main__":
    main()
