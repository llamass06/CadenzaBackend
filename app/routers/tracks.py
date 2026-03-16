import os
import shutil
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

# Importamos configuraciones y servicios
from app.config import UPLOAD_DIR, MODEL_NAME, MAX_PROCESOS
from app.services.ai_separation import ejecutar_demucs
from app.services.audio_analysis import analizar_track

# --- NUEVAS IMPORTACIONES: SEGURIDAD Y BBDD ---
from app.database import models
from app.database.database import get_db
from app.auth import get_current_user

router = APIRouter()

# CONCURRENCIA
semaforo_demucs = asyncio.Semaphore(MAX_PROCESOS)

# ARCHIVOS VALIDOS
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

# PUERTA DE ENTRADA A MI SERVIDOR (AHORA PROTEGIDA)
@router.post("/separar")
async def separar_pistas(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),                              # 1. Abrimos conexion a BBDD
    current_user: models.User = Depends(get_current_user)       # 2. Exigimos que este logueado
): 
    """
    Endpoint principal para la separacion de pistas de audio mediante IA.
    Solo accesible para usuarios autenticados.
    """
    
    # 0. VALIDACION DE SEGURIDAD DEL ARCHIVO
    _, file_extension = os.path.splitext(file.filename)
    
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"El formato de archivo introducido no es valido, solo se aceptan: {ALLOWED_EXTENSIONS}"
        )
    
    # 1. GUARDAR ARCHIVO
    safe_filename = file.filename.replace(" ", "_") 
    file_location = os.path.join(UPLOAD_DIR, safe_filename) 
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # Variables de control
    exito_separacion = False
    metadata = {"bpm": 0, "duration": 0} 

    # 2. IA CON SEMAFORO
    async with semaforo_demucs:
        # Demucs (Separacion)
        exito_separacion = await asyncio.to_thread(ejecutar_demucs, file_location)
        
        # Librosa (Analisis)
        if exito_separacion:
            metadata = await asyncio.to_thread(analizar_track, file_location)

    if not exito_separacion:
        # Limpieza si falla la IA
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail="Error al procesar el audio con la IA.")
    
    # 3. CONSTRUIR RUTAS Y URLS
    song_name = os.path.splitext(safe_filename)[0]
    relative_path = f"{MODEL_NAME}/{song_name}"
    
    # Guardamos las rutas relativas para la base de datos
    db_path_piano = f"{relative_path}/piano.mp3"
    db_path_backing = f"{relative_path}/no_piano.mp3"
    
    # --- 4. NUEVO: GUARDAR EN LA BASE DE DATOS ---
    nueva_cancion = models.Song(
        title=song_name,
        path_piano=db_path_piano,
        path_backing=db_path_backing,
        bpm=metadata["bpm"],
        duration=metadata["duration"],
        owner_id=current_user.id  # ¡Aquí está la magia! Vinculamos la canción a este usuario
    )
    db.add(nueva_cancion)
    db.commit()
    db.refresh(nueva_cancion) # Refrescamos para obtener el ID que le ha dado SQLite
    # ---------------------------------------------
    
    # Preparamos las URLs publicas para devolver al movil
    base_url = "http://127.0.0.1:8000/files"
    url_piano = f"{base_url}/{db_path_piano}"
    url_backing = f"{base_url}/{db_path_backing}"
    
    return {
        "status" : "success",
        "song_id": nueva_cancion.id,          # Le decimos al movil el ID de su nueva cancion
        "owner": current_user.username,       # Confirmamos quien es el dueño
        "song_name" : song_name,
        "piano_url" : url_piano,
        "backing_url" : url_backing,
        "bpm": metadata["bpm"],       
        "duration": metadata["duration"] 
    }