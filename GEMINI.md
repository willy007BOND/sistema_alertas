# Proyecto: Sistema de Alertas - Detección de Caídas

## Convenciones de Desarrollo
- **Entorno de Python:** El ambiente de trabajo obligatorio es el entorno Conda `tfmvc`.
- **Ejecución de Comandos:** Todos los scripts de Python deben ejecutarse usando `conda run -n tfmvc python <script.py>`.
- **Estructura de Datos:** El dataset unificado se centraliza en `/Volumes/Echo 13 SSD/YOLO_DATASET_UNIFIED` siguiendo el formato YOLO (images/train, images/val, labels/train, labels/val).
- **Prefijos:** Cada dataset nuevo debe usar un prefijo único (ej: `IMVIA_`, `KUMAR_`) para evitar colisiones de nombres.
