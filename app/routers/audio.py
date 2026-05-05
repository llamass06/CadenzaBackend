"""
Módulo de enrutamiento para operaciones de subida de audio temporales.

Este módulo define las rutas (endpoints) de FastAPI encargadas de recibir
y almacenar archivos de audio subidos por el cliente antes de ser procesados.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

router = APIRouter(prefix="/api/audio", tags=["Audio"])

# Creamos una carpeta temporal donde se guardarán los audios al subirlos
UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    """
    Sube un archivo de audio al servidor y lo almacena temporalmente.
    
    Este endpoint recibe un archivo a través de form-data, verifica que 
    su tipo de contenido sea de audio, y lo guarda en el directorio 
    temporal configurado (UPLOAD_DIR).
    
    Args:
        file (UploadFile): Archivo subido por el cliente. Debe ser un archivo de audio.
        
    Returns:
        dict: Un diccionario con el mensaje de éxito, el nombre del archivo y la ruta donde se guardó.
        
    Raises:
        HTTPException: 
            - 400 si el archivo no es un audio válido.
            - 500 si ocurre un error en el guardado del archivo.
    """
    # 1. Validación de seguridad extra: comprobar que realmente es un audio
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo no es un formato de audio válido.")

    # 2. Generar la ruta donde guardaremos el archivo físicamente
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # 3. Guardar el archivo en el disco duro de forma segura
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")
    finally:
        # Siempre es buena práctica cerrar el archivo de memoria
        file.file.close()

    # 4. Devolver una respuesta de éxito al frontend
    return {
        "mensaje": "Pista de audio subida correctamente",
        "filename": file.filename,
        "ruta": file_path
    }