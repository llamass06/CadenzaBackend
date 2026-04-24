from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

router = APIRouter(prefix="/api/audio", tags=["Audio"])

# Creamos una carpeta temporal donde se guardarán los audios al subirlos
UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
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