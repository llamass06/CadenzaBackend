import os
import shutil
"""
Utilidades de archivos (Shell Utilities).
Lo necesito especificamente para coger el archivo que sube el usuario
(que llega a la memoria temporal) y guardarlo bien en el disco duro.
"""
import asyncio
"""
Para la asincronia.
Es clave para gestionar el Semaforo (la cola de espera).
Permite mandar el proceso pesado a "segundo plano" para que el servidor
no se quede congelado mientras procesa una cancion.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
"""
APIRouter: Permite crear un "sub-aplicacion" o grupo de rutas. Asi no tenemos todo en el main.py.
UploadFile y File: Herramientas para manejar la subida de archivos binarios (el audio).
HTTPException: Para devolver errores HTTP estandar (como 500 o 404) si algo sale mal.
"""

from app.config import UPLOAD_DIR, MODEL_NAME, MAX_PROCESOS
"""
Importo las constantes globales desde config.py.
Esto es una buena practica para no tener rutas ni nombres de modelos escritos a mano ("hardcoded")
repetidos por varios sitios. Si cambia el modelo, solo lo cambio en config.py.
"""

from app.services.ai_separation import ejecutar_demucs
"""
Logica de negocio para la separacion de audio.

Este modulo procesa la peticion y dependiendo si es valida o no, procesa y envia el resultado o lanza una excepcion
en caso de que sea necesario.
"""
from app.services.audio_analysis import analizar_track
"""
Logica de negocio para el analisis de la obra (calcular bpm)

Usando la Librosa, calcula que tempo debe de tener la obra para enviarlo en conjunto en el JSON final.
"""


router = APIRouter()
"""
Esto es como una miniAPI dentro de la API central, ayuda mucho a modularizar, para que ek main no sea superlargo y si en el futuro quiero agregar usuarios o ago asi pues en esta carpeta cargo el modulo de la miniapi sobre todo lo referente a los usuarios.

Este modulo se encarga de la separacion y el analisis de las obras que se suban
"""

# CONCURRENCIA
semaforo_demucs = asyncio.Semaphore(MAX_PROCESOS)
"""
MAX_PROCESOS indica cuantas canciones se pueden procesar a la vez, por falta de hardware, y para mantener la calidad de las salidas resultantes, solo puedo procesar una sola obra a la vez. No he probado con mas, pero seguramente mi portatil empiece a echar fuego por los ventiladores.

semaforo_demucs es como un semaforo normal de psp, es el que va dejando pasar a los usuarios, si hay uno que esta procesando una cancion, el siguiente que quiera entrar se pondra en cola hasta que salga el que estaba etc.
"""


# ARCHIVOS VALIDOS
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

# PUERTA DE ENTRADA A MI SERVIDOR
@router.post("/separar")
async def separar_pistas(file: UploadFile = File(...)): # file es la key para postman => CUIDADO CON ESTO
    """
    Endpoint principal para la separacion de pistas de audio mediante IA.
    
    Uso POST pq el usuario va a enviar datos (.mp3)
    Los 3 puntos en File(...) son para que el hecho de que se suba un archivo sea obligatorio 
    
    Este endpoint recibe un archivo de audio, lo guarda temporalmente y lo procesa
    utilizando el modelo Demucs para separar el piano del resto de instrumentos.
    Gestiona la concurrencia mediante un semaforo para evitar saturar el servidor.

    :param file: El archivo de audio binario (MP3, WAV, etc.) subido por el usuario que se desea procesar.
    :type file: UploadFile
    :return: Un diccionario JSON con el estado del proceso ('success'), el nombre identificado de la obra y las URLs publicas para descargar o reproducir las pistas separadas (piano y acompañamiento).
    :rtype: dict
    """
    
    #0. Obtenemos la extension y comprobamos que este en ALLOWED_EXTENSIONS, sino elevamos una HTTPEXCEPTION
    _, file_extension = os.path.splitext(file.filename)
    
    if file_extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail= f"El formato de archivo introducido no es valido, solo se aceptan: {ALLOWED_EXTENSIONS}")
    
    #1. Guardar archivo
    safe_filename = file.filename.replace(" ", "_") # Para evitar errores humanos a la hora de nombrar archivos
    file_location = os.path.join(UPLOAD_DIR, safe_filename) # Que guapo, son las cosas que haciamos en primero
    
    #with es para abrir de manera segura
    # wb+ => write binary update
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # Variables de control para la IA y el Analisis
    exito_separacion = False
    metadata = {"bpm": 0, "duration": 0} # Valores por defecto por si falla el analisis

    #2. IA pero con el SEMAFORO
    async with semaforo_demucs:
        # Demucs (Separacion)
        exito_separacion = await asyncio.to_thread(ejecutar_demucs, file_location)
        
        # Librosa (Analisis) - Solo si la separacion fue bien
        # Aprovechamos el turno del semaforo para analizar sin bloquear
        if exito_separacion:
            metadata = await asyncio.to_thread(analizar_track, file_location)

    if not exito_separacion:
        raise HTTPException(status_code=500, detail="Error al procesar el audio con la IA.")
    
    #3. Construir la URL
    song_name = os.path.splitext(safe_filename)[0]
    relative_path = f"{MODEL_NAME}/{song_name}"
    
    # CUIDAO => Las urls ahora son en local
    base_url = "http://127.0.0.1:8000/files"
    url_piano = f"{base_url}/{relative_path}/piano.mp3"
    url_backing = f"{base_url}/{relative_path}/no_piano.mp3"
    
    #---------------------
    print(url_piano)
    # http://127.0.0.1:8000/files/piano.mp3
    print(url_backing)
    # http://127.0.0.1:8000/files/no_piano.mp3
    #---------------------
    
    return {
        "status" : "success",
        "song_name" : song_name,
        "piano_url" : url_piano,
        "backing_url" : url_backing,
        "bpm": metadata["bpm"],       
        "duration": metadata["duration"] 
    }