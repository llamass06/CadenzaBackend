import os
import shutil
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR, MODEL_NAME, MAX_PROCESOS, OUTPUT_DIR
from app.services.ai_separation import ejecutar_demucs
from app.services.audio_analysis import analizar_track

from app.database import models
from app.database.database import get_db
from app.auth import get_current_user

# NUEVO: Importamos el generador de contexto
from app.routers.contexto import generar_contexto_obra, ObraRequest

router = APIRouter()
semaforo_demucs = asyncio.Semaphore(MAX_PROCESOS)
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

@router.post("/separar")
async def separar_pistas(
    title: str = Form(...),                            
    artist: str = Form(None),                         
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
): 
    _, file_extension = os.path.splitext(file.filename)
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no válido. Aceptados: {ALLOWED_EXTENSIONS}"
        )
    
    safe_filename = f"user_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename) 
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    exito_separacion = False
    metadata = {"bpm": 0, "duration": 0} 

    async with semaforo_demucs:
        exito_separacion = await asyncio.to_thread(ejecutar_demucs, file_location)
        if exito_separacion:
            metadata = await asyncio.to_thread(analizar_track, file_location)

    if not exito_separacion:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail="Error en el procesamiento de audio.")
    
    song_folder = os.path.splitext(safe_filename)[0]
    relative_path = f"{MODEL_NAME}/{song_folder}"
    db_path_backing = f"{relative_path}/no_piano.mp3"
    
    # Eliminar el archivo piano.mp3 para no guardarlo
    path_piano_to_delete = os.path.join(OUTPUT_DIR, relative_path, "piano.mp3")
    if os.path.exists(path_piano_to_delete):
        os.remove(path_piano_to_delete)
    
    # --- NUEVO: PEDIR A GEMINI MIENTRAS SE GUARDA ---
    texto_contexto = "Información no disponible."
    try:
        query_ia = f"{title} de {artist}" if artist else title
        res_ia = await generar_contexto_obra(ObraRequest(nombre_obra=query_ia))
        texto_contexto = res_ia["contexto"]
    except Exception as e:
        print(f"Error generando contexto IA: {e}")

    nueva_cancion = models.Song(
        title=title,               
        artist=artist,             
        path_piano=None,            
        path_backing=db_path_backing,
        bpm=metadata["bpm"],
        duration=metadata["duration"],
        contexto=texto_contexto, # <-- GUARDADO EN BBDD
        owner_id=current_user.id  
    )
    db.add(nueva_cancion)
    db.commit()
    db.refresh(nueva_cancion)
    
    base_url = "http://127.0.0.1:8000/files"
    
    return {
        "status" : "success",
        "song_id": nueva_cancion.id,
        "title": title,
        "artist": artist,
        "backing_url" : f"{base_url}/{db_path_backing}",
        "bpm": metadata["bpm"],
        "contexto": texto_contexto # <-- SE LO DEVOLVEMOS A REACT
    }

@router.get("/mis-obras")
async def obtener_mis_obras(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    canciones = db.query(models.Song).filter(models.Song.owner_id == current_user.id).order_by(models.Song.id.desc()).all()
    
    base_url = "http://127.0.0.1:8000/files"
    resultado = []
    
    for c in canciones:
        resultado.append({
            "id": c.id,
            "title": c.title,
            "artist": c.artist,    
            "bpm": c.bpm,
            "duration": c.duration,
            "contexto": c.contexto, # <-- NUEVO: EL HISTORIAL AHORA SABE EL CONTEXTO
            "backing_url": f"{base_url}/{c.path_backing}" if c.path_backing else None,
            "piano_url": f"{base_url}/{c.path_piano}" if c.path_piano else None 
        })
        
    return resultado

@router.delete("/obras/{obra_id}")
async def eliminar_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    obra = db.query(models.Song).filter(models.Song.id == obra_id, models.Song.owner_id == current_user.id).first()
    
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada.")

    try:
        if obra.path_backing:
            full_path = os.path.join(OUTPUT_DIR, obra.path_backing)
            folder_path = os.path.dirname(full_path)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)

        db.delete(obra)
        db.commit()
        return {"message": "Obra eliminada correctamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))