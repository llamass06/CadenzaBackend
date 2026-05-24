"""
Módulo principal de gestión de obras musicales (tracks).

Este módulo define los endpoints centrales de la aplicación:
- POST /separar: Sube un audio y despacha el procesamiento con Demucs en segundo plano.
  Responde inmediatamente con un task_id para que el frontend haga polling.
- GET /separar/status/{task_id}: Permite al frontend consultar el estado de una tarea.
- GET /cola-estado: Devuelve el estado de saturación del servidor.
- GET /mis-obras: Devuelve el historial de obras procesadas del usuario autenticado.
- DELETE /obras/{obra_id}: Elimina una obra de la BBDD y sus archivos del disco.

Utiliza un semáforo para limitar las peticiones concurrentes a Demucs y evitar
desbordamientos de memoria en el servidor.
"""

import os
import shutil
import asyncio
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR, MODEL_NAME, MAX_PROCESOS, OUTPUT_DIR
from app.services.ai_separation import ejecutar_demucs
from app.services.audio_analysis import analizar_track

from app.database import models
from app.database.database import get_db, SessionLocal
from app.auth import get_current_user

# Importamos el generador de contexto musicológico de Gemini
from app.routers.contexto import generar_contexto_obra, ObraRequest

router = APIRouter()
load_dotenv()

# Semáforo que limita el número de procesos de Demucs simultáneos (configurado en app.config)
semaforo_demucs = asyncio.Semaphore(MAX_PROCESOS)

# Contadores globales del estado de la cola de Demucs:
#   tareas_activas    — peticiones que han llegado al servidor (esperando + procesando)
#   tareas_en_proceso — peticiones que han adquirido el semáforo y están ejecutando Demucs
tageas_en_proceso_lock = asyncio.Lock()
tareas_activas = 0
tareas_en_proceso = 0
lock_contador = asyncio.Lock()

# Formatos de audio que el servidor acepta para su procesamiento
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

# Definimos la URL base del servidor para construir enlaces estáticos
base_url = os.getenv("BASE_URL")

# ─────────────────────────────────────────────────────────────────────────────
# Almacén en memoria de tareas de separación.
# Clave: task_id (str UUID)
# Valor: dict con campo 'status' y opcionalmente 'result' o 'error'
#
# Estados posibles:
#   "processing" → Demucs aún está corriendo.
#   "success"    → Separación completada. 'result' contiene los datos finales.
#   "error"      → Falló. 'error' contiene el mensaje de error.
#
# Nota: este diccionario vive en la RAM del proceso. Si el servidor se reinicia,
# las tareas pendientes se pierden (comportamiento aceptable para este caso de uso).
# ─────────────────────────────────────────────────────────────────────────────
tareas_separacion: dict = {}


async def procesar_audio_background(
    task_id: str,
    file_location: str,
    safe_filename: str,
    title: str,
    artist: str,
    user_id: int,
):
    """
    Función de procesamiento pesado que corre en segundo plano (BackgroundTask).

    Ejecuta Demucs bajo el semáforo para controlar la concurrencia, analiza el
    audio resultante para obtener BPM/duración, consulta a Gemini y guarda el
    resultado en la base de datos con una sesión creada manualmente (ya que esta
    función no tiene acceso al ciclo de vida de una petición HTTP normal).

    Al finalizar (tanto en éxito como en error), actualiza tareas_separacion[task_id]
    para que el endpoint GET /separar/status/{task_id} informe al frontend.

    Args:
        task_id (str): Identificador único de la tarea generado en el endpoint POST.
        file_location (str): Ruta absoluta en disco al archivo de audio subido.
        safe_filename (str): Nombre seguro del archivo para construir rutas de salida.
        title (str): Título de la obra enviado por el usuario.
        artist (str): Autor de la obra (puede ser cadena vacía).
        user_id (int): ID del usuario autenticado para guardar el registro en la BBDD.
    """
    global tareas_activas, tareas_en_proceso

    try:
        exito_separacion = False
        metadata = {"bpm": 0, "duration": 0}

        # El semáforo garantiza que solo MAX_PROCESOS instancias de Demucs corren a la vez.
        # Al adquirirlo, incrementamos tareas_en_proceso para que /cola-estado pueda
        # distinguir las peticiones que están procesando de las que aún esperan en cola.
        async with semaforo_demucs:
            async with lock_contador:
                tareas_en_proceso += 1
            try:
                exito_separacion = await asyncio.to_thread(ejecutar_demucs, file_location)
                if exito_separacion:
                    # Analizar BPM y duración solo si la separación fue exitosa
                    metadata = await asyncio.to_thread(analizar_track, file_location)
            finally:
                async with lock_contador:
                    tareas_en_proceso = max(0, tareas_en_proceso - 1)

        if not exito_separacion:
            # Limpiar el archivo subido si Demucs falla para no dejar basura en disco
            if os.path.exists(file_location):
                os.remove(file_location)
            tareas_separacion[task_id] = {
                "status": "error",
                "error": "Error en el procesamiento de audio con Demucs."
            }
            return

        # Construir rutas relativas para almacenarlas en la BBDD
        song_folder = os.path.splitext(safe_filename)[0]
        relative_path = f"{MODEL_NAME}/{song_folder}"
        db_path_backing = f"{relative_path}/no_piano.mp3"

        # Demucs genera dos archivos (piano.mp3 y no_piano.mp3); eliminamos piano.mp3 para ahorrar espacio
        path_piano_to_delete = os.path.join(OUTPUT_DIR, relative_path, "piano.mp3")
        if os.path.exists(path_piano_to_delete):
            os.remove(path_piano_to_delete)

        # Consultar a Gemini el contexto musicológico de la obra
        texto_contexto = "Información no disponible."
        try:
            query_ia = f"{title} de {artist}" if artist else title
            res_ia = await generar_contexto_obra(ObraRequest(nombre_obra=query_ia))
            texto_contexto = res_ia["contexto"]
        except Exception as e:
            # Si Gemini falla, no bloqueamos el proceso; simplemente se guarda sin contexto
            print(f"Error generando contexto IA: {e}")

        # Crear el registro de la canción en la base de datos.
        # Como esta función corre fuera del ciclo de vida de una petición HTTP,
        # debemos crear nuestra propia sesión de BBDD manualmente en lugar de
        # usar la dependencia Depends(get_db).
        db: Session = SessionLocal()
        try:
            nueva_cancion = models.Song(
                title=title,
                artist=artist,
                path_piano=None,        # El piano.mp3 se elimina, así que no se referencia
                path_backing=db_path_backing,
                bpm=metadata["bpm"],
                duration=metadata["duration"],
                contexto=texto_contexto,
                owner_id=user_id
            )
            db.add(nueva_cancion)
            db.commit()
            db.refresh(nueva_cancion)

            # Marcar la tarea como exitosa con los datos finales para el frontend
            tareas_separacion[task_id] = {
                "status": "success",
                "result": {
                    "status": "success",
                    "song_id": nueva_cancion.id,
                    "title": title,
                    "artist": artist,
                    "backing_url": f"{base_url}/files/{db_path_backing}",
                    "bpm": metadata["bpm"],
                    "contexto": texto_contexto,
                }
            }
        except Exception as e:
            db.rollback()
            tareas_separacion[task_id] = {
                "status": "error",
                "error": f"Error guardando en base de datos: {str(e)}"
            }
        finally:
            db.close()

    except Exception as e:
        tareas_separacion[task_id] = {
            "status": "error",
            "error": f"Error inesperado durante el procesamiento: {str(e)}"
        }
    finally:
        # Decrementar siempre el contador de tareas activas al finalizar, haya éxito o error
        async with lock_contador:
            tareas_activas = max(0, tareas_activas - 1)


@router.post("/separar")
async def separar_pistas(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    artist: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Recibe el audio, lo guarda en disco y despacha el procesamiento en segundo plano.

    A diferencia de la versión anterior (que bloqueaba hasta que Demucs terminaba),
    este endpoint responde inmediatamente con un 'task_id'. El frontend usará ese
    identificador para hacer polling al endpoint GET /separar/status/{task_id} y
    saber cuándo ha terminado. Esto elimina el problema de timeout en canciones largas.

    Args:
        background_tasks (BackgroundTasks): Inyectado por FastAPI para registrar tareas en background.
        title (str): Título de la obra musical, enviado como campo de formulario.
        artist (str, optional): Nombre del autor/compositor. Puede ser None.
        file (UploadFile): Archivo de audio a procesar.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        current_user (models.User): Usuario autenticado, obtenido del token JWT.

    Returns:
        dict: {"status": "processing", "task_id": "<uuid>"} para que el frontend empiece el polling.

    Raises:
        HTTPException:
            - 400 Si el formato del archivo no está entre los permitidos.
    """
    global tareas_activas

    # Validar que la extensión sea de un formato de audio admitido
    _, file_extension = os.path.splitext(file.filename)
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no válido. Aceptados: {ALLOWED_EXTENSIONS}"
        )

    # Registrar la llegada de la petición en el contador global
    async with lock_contador:
        tareas_activas += 1

    # Construir un nombre de archivo único para evitar sobreescribir obras de otros usuarios
    safe_filename = f"user_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)

    # Guardar el archivo recibido en el disco (operación síncrona y rápida)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    # Generar un identificador único para esta tarea de procesamiento
    task_id = str(uuid.uuid4())

    # Registrar la tarea como "en proceso" inmediatamente en el almacén en memoria
    tareas_separacion[task_id] = {"status": "processing"}

    # Despachar el procesamiento pesado en segundo plano (no bloquea la respuesta HTTP)
    background_tasks.add_task(
        procesar_audio_background,
        task_id,
        file_location,
        safe_filename,
        title,
        artist or "",
        current_user.id,
    )

    # Responder inmediatamente al frontend con el task_id para que empiece el polling
    return {"status": "processing", "task_id": task_id}


@router.get("/separar/status/{task_id}")
async def obtener_estado_tarea(task_id: str):
    """
    Consulta el estado actual de una tarea de separación de pistas.

    El frontend llama a este endpoint cada pocos segundos (polling) para saber
    si Demucs ha terminado de procesar el audio. Cuando el status es 'success',
    devuelve los datos finales (backing_url, bpm, contexto) dentro de 'result'.
    Si es 'error', devuelve el mensaje de error para mostrarlo al usuario.

    Args:
        task_id (str): Identificador único de la tarea, obtenido de POST /separar.

    Returns:
        dict: Estado actual de la tarea con sus datos o error.

    Raises:
        HTTPException:
            - 404 Si el task_id no existe en el almacén de tareas.
    """
    tarea = tareas_separacion.get(task_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    return tarea


@router.get("/cola-estado")
async def obtener_estado_cola():
    """
    Devuelve el estado actual de la cola de procesamiento de Demucs.

    Permite al frontend hacer polling para detectar saturación del servidor
    y mostrar un aviso informativo al usuario mientras espera su turno.

    Returns:
        dict: Número de tareas activas, tareas esperando en cola y flag de saturación.
    """
    global tareas_activas, tareas_en_proceso
    # tareas_esperando = peticiones llegadas al servidor que aún no han entrado al semáforo
    tareas_esperando = max(0, tareas_activas - tareas_en_proceso)
    return {
        "tareas_activas": tareas_activas,
        "tareas_en_proceso": tareas_en_proceso,
        "tareas_esperando": tareas_esperando,
        "saturado": tareas_esperando >= 1
    }


@router.get("/mis-obras")
async def obtener_mis_obras(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Devuelve el historial de obras procesadas del usuario autenticado.

    Consulta la base de datos y retorna todas las canciones que pertenecen
    al usuario actual, ordenadas de más reciente a más antigua. Construye
    las URLs de streaming para el acompañamiento y el piano (si existiera).

    Args:
        db (Session): Sesión de la base de datos inyectada como dependencia.
        current_user (models.User): Usuario autenticado, obtenido del token JWT.

    Returns:
        list[dict]: Lista de obras del usuario, cada una con id, title, artist,
                    bpm, duration, contexto, backing_url y piano_url.
    """
    canciones = db.query(models.Song).filter(models.Song.owner_id == current_user.id).order_by(models.Song.id.desc()).all()

    resultado = []

    for c in canciones:
        resultado.append({
            "id": c.id,
            "title": c.title,
            "artist": c.artist,
            "bpm": c.bpm,
            "duration": c.duration,
            "contexto": c.contexto,
            "backing_url": f"{base_url}/files/{c.path_backing}" if c.path_backing else None,
            "piano_url": f"{base_url}/files/{c.path_piano}" if c.path_piano else None
        })

    return resultado

@router.delete("/obras/{obra_id}")
async def eliminar_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Elimina una obra del usuario: borra sus archivos del disco y su registro de la BBDD.

    Solo puede eliminar obras que pertenezcan al usuario autenticado. Primero elimina
    la carpeta completa de la obra en el sistema de archivos (OUTPUT_DIR) y luego
    borra el registro de la base de datos. Si algo falla, hace rollback de la BBDD.

    Args:
        obra_id (int): ID de la obra a eliminar, obtenido de la URL.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        current_user (models.User): Usuario autenticado, obtenido del token JWT.

    Returns:
        dict: Mensaje de confirmación de eliminación exitosa.

    Raises:
        HTTPException:
            - 404 Si la obra no existe o no pertenece al usuario autenticado.
            - 500 Si ocurre un error durante la eliminación de archivos o la BBDD.
    """
    obra = db.query(models.Song).filter(models.Song.id == obra_id, models.Song.owner_id == current_user.id).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada.")

    try:
        if obra.path_backing:
            # Obtener la carpeta padre del acompañamiento y eliminar todo su contenido
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