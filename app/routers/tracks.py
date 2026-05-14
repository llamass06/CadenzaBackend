"""
Módulo principal de gestión de obras musicales (tracks).

Este módulo define los tres endpoints centrales de la aplicación:
- POST /separar: Sube un audio, lo procesa con Demucs (IA de separación),
  genera el contexto de la obra con Gemini y guarda el resultado en la BBDD.
- GET /mis-obras: Devuelve el historial de obras procesadas del usuario autenticado.
- DELETE /obras/{obra_id}: Elimina una obra de la BBDD y sus archivos del disco.

Utiliza un semáforo para limitar las peticiones concurrentes a Demucs y evitar
desbordamientos de memoria en el servidor.
"""

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

# Importamos el generador de contexto musicológico de Gemini
from app.routers.contexto import generar_contexto_obra, ObraRequest

router = APIRouter()

# Semáforo que limita el número de procesos de Demucs simultáneos (configurado en app.config)
semaforo_demucs = asyncio.Semaphore(MAX_PROCESOS)

# Formatos de audio que el servidor acepta para su procesamiento
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

# Definimos la URL base del servidor para construir enlaces estáticos
base_url = os.getenv("BASE_URL")


@router.post("/separar")
async def separar_pistas(
    title: str = Form(...),                            
    artist: str = Form(None),                         
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
): 
    """
    Procesa una obra musical: separa el acompañamiento del piano y la guarda en la BBDD.
    
    Flujo de ejecución:
    1. Valida que la extensión del archivo sea permitida.
    2. Genera un nombre de archivo seguro y único por usuario para evitar colisiones.
    3. Guarda el archivo en el directorio de subidas (UPLOAD_DIR).
    4. Ejecuta Demucs en un hilo separado (controlado por semáforo) para no bloquear el servidor.
    5. Si Demucs tiene éxito, analiza el audio para obtener BPM y duración.
    6. Elimina el archivo piano.mp3 generado por Demucs para ahorrar espacio en disco.
    7. Consulta a Gemini para generar un texto de contexto musicológico de la obra.
    8. Guarda la canción (con su contexto y ruta del acompañamiento) en la base de datos.
    9. Devuelve la URL del acompañamiento y los metadatos al frontend.
    
    Args:
        title (str): Título de la obra musical, enviado como campo de formulario.
        artist (str, optional): Nombre del autor/compositor. Puede ser None.
        file (UploadFile): Archivo de audio a procesar.
        db (Session): Sesión de la base de datos inyectada como dependencia.
        current_user (models.User): Usuario autenticado, obtenido del token JWT.
        
    Returns:
        dict: Estado del procesamiento, ID de la canción, URL del acompañamiento,
              BPM, y el texto de contexto generado por la IA.
              
    Raises:
        HTTPException:
            - 400 Si el formato del archivo no está entre los permitidos.
            - 500 Si Demucs falla durante la separación de pistas.
    """
    # Validar que la extensión sea de un formato de audio admitido
    _, file_extension = os.path.splitext(file.filename)
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no válido. Aceptados: {ALLOWED_EXTENSIONS}"
        )
    
    # Construir un nombre de archivo único para evitar sobreescribir obras de otros usuarios
    safe_filename = f"user_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename) 
    
    # Guardar el archivo recibido en el disco
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    exito_separacion = False
    metadata = {"bpm": 0, "duration": 0} 

    # El semáforo garantiza que solo MAX_PROCESOS instancias de Demucs corren a la vez
    async with semaforo_demucs:
        exito_separacion = await asyncio.to_thread(ejecutar_demucs, file_location)
        if exito_separacion:
            # Analizar BPM y duración solo si la separación fue exitosa
            metadata = await asyncio.to_thread(analizar_track, file_location)

    if not exito_separacion:
        # Limpiar el archivo subido si Demucs falla para no dejar basura en disco
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail="Error en el procesamiento de audio.")
    
    # Construir rutas relativas para almacenarlas en la BBDD
    song_folder = os.path.splitext(safe_filename)[0]
    relative_path = f"{MODEL_NAME}/{song_folder}"
    db_path_backing = f"{relative_path}/no_piano.mp3"
    
    # Demucs genera dos archivos (piano.mp3 y no_piano.mp3); eliminamos piano.mp3 para ahorrar espacio
    path_piano_to_delete = os.path.join(OUTPUT_DIR, relative_path, "piano.mp3")
    if os.path.exists(path_piano_to_delete):
        os.remove(path_piano_to_delete)
    
    # Consultar a Gemini el contexto musicológico de la obra mientras se guarda en BBDD
    texto_contexto = "Información no disponible."
    try:
        query_ia = f"{title} de {artist}" if artist else title
        res_ia = await generar_contexto_obra(ObraRequest(nombre_obra=query_ia))
        texto_contexto = res_ia["contexto"]
    except Exception as e:
        # Si Gemini falla, no bloqueamos el proceso; simplemente se guarda sin contexto
        print(f"Error generando contexto IA: {e}")

    # Crear el registro de la canción en la base de datos
    nueva_cancion = models.Song(
        title=title,               
        artist=artist,             
        path_piano=None,            # El piano.mp3 se elimina, así que no se referencia
        path_backing=db_path_backing,
        bpm=metadata["bpm"],
        duration=metadata["duration"],
        contexto=texto_contexto,
        owner_id=current_user.id  
    )
    db.add(nueva_cancion)
    db.commit()
    db.refresh(nueva_cancion)
    
    
    return {
        "status" : "success",
        "song_id": nueva_cancion.id,
        "title": title,
        "artist": artist,
        "backing_url" : f"{base_url}/{db_path_backing}",
        "bpm": metadata["bpm"],
        "contexto": texto_contexto
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