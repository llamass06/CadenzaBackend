"""
Módulo principal de gestión de obras musicales (tracks).

Este módulo define los endpoints centrales de la aplicación para procesar,
listar y eliminar obras musicales. La lógica de negocio pesada ha sido delegada
a `audio_processing_service` y la gestión de estado a `demucs_manager`.
"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR, OUTPUT_DIR, BASE_URL, MAX_OBRAS
from app.database import models
from app.database.database import get_db
from app.auth import get_current_user
from app.services.demucs_manager import task_manager
from app.services.audio_processing_service import procesar_audio_background, limpiar_archivos
from app.utils.file_utils import save_upload_file

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

@router.post("/separar")
async def separar_pistas(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    artist: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    _, file_extension = os.path.splitext(file.filename)
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato no válido. Aceptados: {ALLOWED_EXTENSIONS}")

    obras_actuales = db.query(models.Song).filter(models.Song.owner_id == current_user.id).count()
    if obras_actuales >= MAX_OBRAS:
        raise HTTPException(
            status_code=400,
            detail=f"Límite de {MAX_OBRAS} obras alcanzado. Elimina una obra antes de subir otra."
        )

    task_id = str(uuid.uuid4())
    await task_manager.registrar_tarea(task_id)

    safe_filename = f"user_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)

    save_upload_file(file, file_location)

    background_tasks.add_task(
        procesar_audio_background,
        task_id,
        file_location,
        safe_filename,
        title,
        artist or "",
        current_user.id,
    )

    return {"status": "processing", "task_id": task_id}

@router.get("/separar/status/{task_id}")
async def obtener_estado_tarea(task_id: str):
    tarea = task_manager.obtener_tarea(task_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    return tarea

@router.get("/cola-estado")
async def obtener_estado_cola():
    return task_manager.estado_cola()

@router.get("/mis-obras")
async def obtener_mis_obras(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    canciones = db.query(models.Song).filter(models.Song.owner_id == current_user.id).order_by(models.Song.id.desc()).all()
    
    return [
        {
            "id": c.id,
            "title": c.title,
            "artist": c.artist,
            "bpm": c.bpm,
            "duration": c.duration,
            "contexto": c.contexto,
            "backing_url": f"{BASE_URL}/files/{c.path_backing}" if c.path_backing else None,
            "piano_url": f"{BASE_URL}/files/{c.path_piano}" if c.path_piano else None
        }
        for c in canciones
    ]

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
            limpiar_archivos([folder_path])

        db.delete(obra)
        db.commit()
        return {"message": "Obra eliminada correctamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))