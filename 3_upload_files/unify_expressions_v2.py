import shutil
import os
from pathlib import Path
from tqdm import tqdm

# Rutas
SOURCE_BASE = Path("/Volumes/Echo 13 SSD/TFM/images/EXPRESIONES")
TARGET_BASE = Path("/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED")

# Mapeo de clases estándar (ajustar según necesidad del modelo)
# 0: angry, 1: disgust, 2: fear, 3: happy, 4: neutral, 5: sad, 6: surprise
CLASS_MAP = {
    "angry": 0,
    "disgust": 1,
    "fear": 2,
    "happy": 3,
    "neutral": 4,
    "sad": 5,
    "surprise": 6
}

# Datasets con estructura de carpetas por clase (sin TXT)
DATASETS_CLASSIFICATION = [
    {
        "name": "FER2013",
        "path": SOURCE_BASE / "FER2013/expresiones/images_expresiones",
        "splits": {"train": "train", "test": "val"} # Mapeo de split origen:destino
    },
    {
        "name": "FACE_RECOGNITION",
        "path": SOURCE_BASE / "FACE_EXPRESSION_RECOGNITION/images/images",
        "splits": {"train": "train", "validation": "val"}
    }
]

def setup_structure(base_path):
    print(f"Verificando estructura en {base_path}...")
    for folder in ["images", "labels"]:
        for split in ["train", "val", "test"]:
            (base_path / folder / split).mkdir(parents=True, exist_ok=True)

def process_classification_dataset():
    setup_structure(TARGET_BASE)
    
    for ds in DATASETS_CLASSIFICATION:
        name = ds["name"]
        print(f"\nProcesando {name} (Generando etiquetas YOLO)...")
        
        for src_split, target_split in ds["splits"].items():
            split_path = ds["path"] / src_split
            if not split_path.exists():
                print(f"  Aviso: No se encontró split {src_split} en {split_path}")
                continue
            
            # Recorrer cada carpeta de clase
            for class_name, class_id in CLASS_MAP.items():
                class_dir = split_path / class_name
                if not class_dir.exists():
                    continue
                
                images = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png"))
                print(f"  - {class_name}: {len(images)} imágenes")
                
                for img_path in tqdm(images, desc=f"{name} {class_name}", leave=False):
                    new_name = f"{name}_{img_path.name}"
                    target_img = TARGET_BASE / "images" / target_split / new_name
                    target_lbl = TARGET_BASE / "labels" / target_split / f"{name}_{img_path.stem}.txt"
                    
                    # 1. Saltar si ya existe
                    if target_img.exists():
                        continue
                    
                    # 2. Copiar Imagen
                    try:
                        shutil.copy2(img_path, target_img)
                        
                        # 3. Crear Label (Cara completa: class_id, center_x, center_y, width, height)
                        with open(target_lbl, "w") as f:
                            f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")
                    except Exception as e:
                        print(f"Error procesando {img_path}: {e}")

if __name__ == "__main__":
    process_classification_dataset()
    print("\n¡Unificación V2 (FER2013 + FaceRec) finalizada con éxito!")
    print(f"Resultados en: {TARGET_BASE}")
