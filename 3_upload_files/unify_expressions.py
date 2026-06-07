import shutil
import os
from pathlib import Path
from tqdm import tqdm

# Rutas
SOURCE_BASE = Path("/Volumes/Echo 13 SSD/TFM/images/EXPRESIONES")
TARGET_BASE = Path("/Volumes/Echo 13 SSD/YOLO_EXPRESIONES_UNIFIED")

# Datasets identificados con estructura YOLO o similar
DATASETS = [
    {
        "name": "AFFECTNET",
        "path": SOURCE_BASE / "AFFECTNET_YOLO_FORMAT/YOLO_format",
        "splits": ["train", "valid", "test"]
    },
    {
        "name": "A8_FACIAL",
        "path": SOURCE_BASE / "A8_FACIAL_EXPRESSIONS_FOR_YOLO/9 Facial Expressions you need",
        "splits": ["train", "valid", "test"]
    }
]

def setup_structure(base_path):
    print(f"Preparando estructura en {base_path}...")
    for folder in ["images", "labels"]:
        for split in ["train", "val", "test"]:
            (base_path / folder / split).mkdir(parents=True, exist_ok=True)

def centralize():
    setup_structure(TARGET_BASE)
    
    for ds in DATASETS:
        name = ds["name"]
        ds_path = ds["path"]
        print(f"\nProcesando {name}...")
        
        for split in ds["splits"]:
            # Normalizar nombre del split (valid -> val)
            target_split = "val" if split == "valid" else split
            
            img_src = ds_path / split / "images"
            lbl_src = ds_path / split / "labels"
            
            if not img_src.exists():
                print(f"  Aviso: No se encontró carpeta de imágenes en {img_src}")
                continue
            
            images = list(img_src.glob("*.jpg")) + list(img_src.glob("*.png"))
            print(f"  Copiando {len(images)} imágenes de {name} ({split})...")
            
            for img_path in tqdm(images, desc=f"{name} ({split})"):
                new_name = f"{name}_{img_path.name}"
                
                # Copiar Imagen
                shutil.copy2(img_path, TARGET_BASE / "images" / target_split / new_name)
                
                # Copiar Label
                lbl_path = lbl_src / f"{img_path.stem}.txt"
                if lbl_path.exists():
                    shutil.copy2(lbl_path, TARGET_BASE / "labels" / target_split / f"{name}_{lbl_path.name}")

if __name__ == "__main__":
    centralize()
    print("\n¡Unificación de expresiones finalizada con éxito!")
