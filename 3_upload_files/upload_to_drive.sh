#!/bin/bash

SOURCE="/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED"
DEST="gdrive:TFM/EXPRESIONES/YOLO_EXPRESIONES_UNIFIED"
LOG_DIR="$HOME/rclone_logs"

mkdir -p "$LOG_DIR"

FOLDERS=(
  "images/train"
  "images/val"
  "images/test"
  "labels/train"
  "labels/val"
  "labels/test"
)

echo "================================================"
echo " SUBIDA A GOOGLE DRIVE — DATASET MASIVO"
echo " ADVERTENCIA: images/train tiene ~390.000 archivos"
echo " El escaneo inicial tarda ~10-15 min antes de empezar"
echo " Inicio: $(date '+%H:%M:%S')"
echo "================================================"

TOTAL=${#FOLDERS[@]}
COUNT=0

for folder in "${FOLDERS[@]}"; do
  COUNT=$((COUNT + 1))
  echo ""
  echo "[$COUNT/$TOTAL] Subiendo: $folder  ($(date '+%H:%M:%S'))"
  echo "------------------------------------------------"
  echo "Escaneando archivos locales... espera hasta ver los primeros bytes transferidos"

  rclone copy \
    "$SOURCE/$folder" \
    "$DEST/$folder" \
    --no-traverse \
    --transfers 8 \
    --drive-chunk-size 64M \
    --drive-batch-size 1000 \
    --drive-batch-mode robotics \
    --stats 5s \
    --stats-one-line \
    --log-file "$LOG_DIR/${folder//\//_}.log" \
    --log-level INFO \
    --progress

  if [ $? -eq 0 ]; then
    echo "✓ Completado: $folder  ($(date '+%H:%M:%S'))"
  else
    echo "✗ ERROR en: $folder — revisa $LOG_DIR/${folder//\//_}.log"
  fi
done

echo ""
echo "================================================"
echo " SUBIDA COMPLETA — $(date '+%H:%M:%S')"
echo "================================================"
