"""
Módulo de utilidades para el manejo de archivos.
"""
import shutil
from fastapi import UploadFile

def save_upload_file(upload_file: UploadFile, destination_path: str):
    """
    Guarda un UploadFile de FastAPI en la ruta de destino.
    """
    try:
        with open(destination_path, "wb+") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()
