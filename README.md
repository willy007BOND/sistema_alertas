## Configuración del dataset (data.yaml)

Los comandos de entrenamiento y validación (`yolo detect train/val ... data=data.yaml`)
requieren un archivo `data.yaml` que **no se incluye en este repositorio**, dado que los
datasets no se redistribuyen. Para crearlo:

1. Descargue los datasets desde Kaggle y ejecute los notebooks de preprocesamiento
   y particionamiento 70/15/15 (ver memoria, secciones 5.2 y 6.2.2).
2. Copie `data.yaml.example` como `data.yaml` y ajuste las rutas a la ubicación
   local de sus datos.