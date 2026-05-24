"""
Módulo de enrutamiento para operaciones de subida de audio temporales.

Este módulo define las rutas (endpoints) de FastAPI encargadas de recibir
y almacenar archivos de audio subidos por el cliente antes de ser procesados.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import os

from app.config import UPLOAD_DIR
from app.utils.file_utils import save_upload_file

router = APIRouter(prefix="/api/audio", tags=["Audio"])

@router.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    """
    Sube un archivo de audio al servidor y lo almacena temporalmente.
    """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo no es un formato de audio válido.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    try:
        save_upload_file(file, file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    return {
        "mensaje": "Pista de audio subida correctamente",
        "filename": file.filename,
        "ruta": file_path
    }