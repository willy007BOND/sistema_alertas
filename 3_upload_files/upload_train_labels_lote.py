#!/usr/bin/env python3
"""
Sube un lote de labels locales de train a Google Drive sin validacion previa.

No borra archivos en Drive. Genera un manifest local con los primeros N .txt
en labels/train y lo entrega a rclone copy mediante --files-from.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

SOURCE_LABELS = "/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED/labels/train"
DEST_LABELS = "gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED/labels/train"
LOG_DIR = Path.home() / "rclone_logs"


def is_appledouble_name(name):
    return name.startswith("._") or "_._" in name


def clean_label_names(names):
    clean = []
    for name in names:
        name = name.strip()
        if name and not is_appledouble_name(name) and name.lower().endswith(".txt"):
            clean.append(name)
    return clean


def load_manifest(manifest_path, limit=None):
    with open(manifest_path, "r", encoding="utf-8") as fh:
        names = clean_label_names(fh)
    if limit:
        names = names[:limit]
    if not names:
        raise RuntimeError(f"El manifest no contiene labels validos: {manifest_path}")
    print(f"  Manifest externo: {manifest_path}")
    print(f"  Labels validos  : {len(names):,}")
    return write_manifest(names), len(names)


def write_manifest(names, suffix="_train_labels.txt"):
    manifest = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8",
    )
    with manifest:
        manifest.write("\n".join(names))
        manifest.write("\n")
    return manifest.name


def build_manifest(source_labels, limit):
    print(f"\n[1/2] Creando manifest con hasta {limit:,} labels locales...")
    print(f"  Origen: {source_labels}")

    names = []
    with os.scandir(source_labels) as entries:
        for entry in entries:
            name = entry.name
            if is_appledouble_name(name) or not name.lower().endswith(".txt"):
                continue
            names.append(name)
            if len(names) % 1000 == 0:
                print(f"  ... {len(names):,} labels agregados al manifest", flush=True)
            if len(names) >= limit:
                break

    if not names:
        raise RuntimeError("No se encontraron labels .txt locales para subir.")

    manifest_path = write_manifest(names)
    print(f"  OK: {len(names):,} labels en manifest")
    print(f"  Manifest temporal: {manifest_path}")
    return manifest_path, len(names)


def upload_manifest(manifest_path, source_labels, dest_labels, args):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "upload_train_labels_lote.log"

    print(f"\n[2/2] Subiendo lote a Drive...")
    print(f"  Destino: {dest_labels}")
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
        source_labels,
        dest_labels,
    ]

    return subprocess.run(cmd).returncode


def write_block_manifest(names, start, end):
    path = Path(tempfile.gettempdir()) / f"train_labels_{start}_{end}.txt"
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(names[start - 1:end]))
        fh.write("\n")
    return path


def start_rclone_block(manifest_path, source_labels, dest_labels, args, start, end):
    log_file = LOG_DIR / f"upload_train_labels_{start}_{end}_no_repisar.log"
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
        source_labels,
        dest_labels,
    ]
    print(f"  Lanzando bloque labels {start}-{end}: {manifest_path}", flush=True)
    return subprocess.Popen(cmd)


def upload_pipeline(args, manifest_path):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "r", encoding="utf-8") as fh:
        names = clean_label_names(fh)
    if args.limit:
        names = names[:args.limit]
    if not names:
        raise RuntimeError("No hay labels validos para pipeline.")

    active = []
    next_start = 1
    completed = 0
    failed = 0

    try:
        while next_start <= len(names) or active:
            while next_start <= len(names) and len(active) < args.pipeline_lanes:
                end = min(next_start + args.pipeline_block_size - 1, len(names))
                block_manifest = write_block_manifest(names, next_start, end)
                proc = start_rclone_block(block_manifest, args.source_labels, args.dest_labels, args, next_start, end)
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
                    print(f"  OK bloque labels {start}-{end}", flush=True)
                else:
                    failed += 1
                    print(f"  ERROR bloque labels {start}-{end}: rclone codigo {code}", flush=True)
            active = still_active

            print(
                f"[PIPELINE LABELS] activos={len(active)} completados={completed} "
                f"fallidos={failed} siguiente={next_start}",
                flush=True,
            )
            if active or next_start <= len(names):
                time.sleep(args.pipeline_poll)
    except KeyboardInterrupt:
        print("\n[PIPELINE LABELS] Interrumpido. Enviando Ctrl+C a carriles activos...")
        for proc, _, _ in active:
            proc.send_signal(2)
        raise

    return 0 if failed == 0 else 1, len(names)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sube un lote de labels train a Drive sin validacion previa."
    )
    parser.add_argument("--limit", type=int, default=15000, help="Cantidad maxima de labels a poner en el manifest.")
    parser.add_argument("--source-labels", default=SOURCE_LABELS)
    parser.add_argument("--dest-labels", default=DEST_LABELS)
    parser.add_argument("--manifest", help="Manifest de labels .txt a subir; util para faltantes exactos.")
    parser.add_argument("--transfers", type=int, default=16)
    parser.add_argument("--checkers", type=int, default=32)
    parser.add_argument("--drive-chunk-size", default="32M")
    parser.add_argument("--tpslimit", type=int, default=8)
    parser.add_argument("--stats", default="10s")
    parser.add_argument("--keep-manifest", action="store_true")
    parser.add_argument("--pipeline", action="store_true", help="Sube labels en bloques paralelos sin repisar.")
    parser.add_argument("--pipeline-lanes", type=int, default=5)
    parser.add_argument("--pipeline-block-size", type=int, default=500)
    parser.add_argument("--pipeline-transfers", type=int, default=4)
    parser.add_argument("--pipeline-checkers", type=int, default=8)
    parser.add_argument("--pipeline-tpslimit", type=int, default=4)
    parser.add_argument("--pipeline-stagger", type=int, default=10)
    parser.add_argument("--pipeline-poll", type=int, default=20)
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 66)
    print("  SUBIDA LOTE LABELS TRAIN SIN VALIDACION")
    print(f"  Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 66)

    if not os.path.isdir(args.source_labels):
        print(f"ERROR: no existe la carpeta local: {args.source_labels}")
        sys.exit(1)

    manifest_path = None
    try:
        if args.manifest:
            manifest_path, total = load_manifest(args.manifest, args.limit)
        else:
            manifest_path, total = build_manifest(args.source_labels, args.limit)
        if args.pipeline:
            code, total = upload_pipeline(args, manifest_path)
        else:
            code = upload_manifest(manifest_path, args.source_labels, args.dest_labels, args)
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
        print(f"  SUBIDA DE LOTE FINALIZADA: {total:,} labels procesados por rclone")
    else:
        print(f"  rclone termino con codigo {code}. Revisa el log.")
        sys.exit(code)
    print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 66)


if __name__ == "__main__":
    main()
