import os
import shutil
import asyncio
from contextlib import contextmanager

from app.config import MODEL_NAME, OUTPUT_DIR, MAX_OBRAS, BASE_URL
from app.services.ai_separation import ejecutar_demucs
from app.services.audio_analysis import analizar_track
from app.database import models
from app.database.database import SessionLocal
from app.services.gemini_service import consultar_contexto_gemini
from app.services.demucs_manager import task_manager

@contextmanager
def db_session_scope():
    """Proporciona un scope transaccional para operaciones en base de datos."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def limpiar_archivos(rutas: list[str]):
    """Elimina archivos o directorios si existen."""
    for ruta in rutas:
        if os.path.isfile(ruta):
            os.remove(ruta)
        elif os.path.isdir(ruta):
            shutil.rmtree(ruta)

async def ejecutar_pipeline_audio(task_id: str, file_location: str) -> tuple[bool, dict]:
    """Ejecuta Demucs y analiza el track, controlando la concurrencia."""
    metadata = {"bpm": 0, "duration": 0}
    async with task_manager.semaforo:
        await task_manager.iniciar_proceso(task_id)
        try:
            exito = await asyncio.to_thread(ejecutar_demucs, file_location)
            if exito:
                metadata = await asyncio.to_thread(analizar_track, file_location)
            return exito, metadata
        finally:
            await task_manager.finalizar_proceso()

async def procesar_audio_background(
    task_id: str,
    file_location: str,
    safe_filename: str,
    title: str,
    artist: str,
    user_id: int,
):
    try:
        exito_separacion, metadata = await ejecutar_pipeline_audio(task_id, file_location)

        if not exito_separacion:
            limpiar_archivos([file_location])
            task_manager.actualizar_estado(task_id, "error", error="Error en el procesamiento de audio con Demucs.")
            return

        song_folder = os.path.splitext(safe_filename)[0]
        relative_path = f"{MODEL_NAME}/{song_folder}"
        db_path_backing = f"{relative_path}/no_piano.mp3"
        
        # Eliminar el archivo de piano.mp3 generado por Demucs
        path_piano_to_delete = os.path.join(OUTPUT_DIR, relative_path, "piano.mp3")
        limpiar_archivos([path_piano_to_delete])

        texto_contexto = await consultar_contexto_gemini(title, artist)

        with db_session_scope() as db:
            obras_actuales = db.query(models.Song).filter(models.Song.owner_id == user_id).count()
            if obras_actuales >= MAX_OBRAS:
                output_folder = os.path.join(OUTPUT_DIR, relative_path)
                limpiar_archivos([output_folder])
                task_manager.actualizar_estado(
                    task_id, "error", 
                    error=f"Límite de {MAX_OBRAS} obras alcanzado. Elimina una obra antes de subir otra."
                )
                return

            nueva_cancion = models.Song(
                title=title,
                artist=artist,
                path_piano=None,
                path_backing=db_path_backing,
                bpm=metadata["bpm"],
                duration=metadata["duration"],
                contexto=texto_contexto,
                owner_id=user_id
            )
            db.add(nueva_cancion)
            db.flush()  # Para obtener el ID antes del commit (manejado por el db_session_scope)
            
            task_manager.actualizar_estado(
                task_id, "success",
                result={
                    "status": "success",
                    "song_id": nueva_cancion.id,
                    "title": title,
                    "artist": artist,
                    "backing_url": f"{BASE_URL}/files/{db_path_backing}",
                    "bpm": metadata["bpm"],
                    "contexto": texto_contexto,
                }
            )

    except Exception as e:
        task_manager.actualizar_estado(task_id, "error", error=f"Error inesperado durante el procesamiento: {str(e)}")
    finally:
        await task_manager.finalizar_tarea()
