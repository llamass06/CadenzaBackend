"""
uvicorn app.main:app --reload
"""

# IMPORTS

from fastapi import FastAPI
"""
FastAPI: La clase principal para arrancar la app.
UploadFile y File: Tipos de datos para decirle a la API que va a recibir un archivo binario (el audio), no texto.
HTTPException: Para lanzar errores controlados (como un 500) si falla la IA, en vez de que explote todo.
"""

from fastapi.staticfiles import StaticFiles
"""
Archivos Estaticos.
Sirve para "hacer publica" la carpeta donde guardo los resultados.
Sin esto, la app movil no tendria una URL para descargar o reproducir los audios.
"""

from fastapi.responses import JSONResponse
"""
Para personalizar las respuestas JSON.
Aunque FastAPI lo hace automatico, lo importo por si necesito cambiar cabeceras o estados mas adelante.
"""

from fastapi.middleware.cors import CORSMiddleware

from app.config import OUTPUT_DIR
from app.routers import tracks
from app.routers import auth # Rutas de seguridad
from app.routers import contexto
from app.routers import audio

# --- NUEVO: CREACIÓN DE TABLAS DE BBDD ---
from app.database import models
from app.database.database import engine

from fastapi import FastAPI

app = FastAPI(
    title = "Cadenza Backend",
    description="""
    -Version 1.0.0
    --------------
    Backend de mi proyecto integrado 'Cadenza'. Se le pasa una obra musical en formato .mp3, y mediante un modelo de IA, separa este audio para lograr otras dos salidas de audio. Una con el acompañamiento (violin, guitarra, tambores, trompetas etc) pero SIN el piano, y otra, menos importante, SOLO con el piano.
    
    -Version 1.1.0
    --------------
    Implementacion de la libreria Librosa, cuyo proposito es de implementar el modulo de deteccion de tempo de las obras analizadas, para proporcionarle al usuario un ritmo base para el metronomo, que mas adelante podra cambiar para ajustarse a sus necesidades.
    
    -Version 1.1.1
    --------------
    Prevenir fallas humanas, que solo puedan subir archivos que FFMPEG y Demucs admitan (osea que solo suban archivos de audio).
    
    -Version 1.2.0
    --------------
    Implementación de base de datos (SQLite), registro de usuarios y autenticación mediante JWT.
    """,
    version="1.2.0"
)

# <-- NUEVO: Configurar CORS
# Le decimos a FastAPI que permita peticiones desde tu frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Permite cualquier cabecera (como el Authorization con el JWT)
)

# Esta instrucción lee los modelos y CREA las tablas físicas en cadenza.db si no existen.
models.Base.metadata.create_all(bind=engine)
# ----------------------------------------

# CONFIGURACION 
"""
Convenio de cambio de versiones:
    -1.0.X => Cuando se arregla un bug pequeño.
    -1.X.0 => Cuando se añade una nueva funcionalidad, pero el resto sigue igual.
    -X.0.0 => Cuando el cambio hace que lo demas deje de funcionalidad (bastante radical btw).
"""


# IMPORTANTE (web)
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")
"""
Montar la carpeta separated para que sea accesible por web.
Esto permite que la app descargue los audios resultantes.
"""

# Incluir las rutas (Endpoints)
# Agrupamos las rutas por "tags" para que en Swagger (/docs) se vea más organizado
app.include_router(auth.router, prefix="/api/auth", tags=["Usuarios y Seguridad"])
app.include_router(tracks.router, prefix="/api/v1", tags=["IA y Pistas"])
app.include_router(contexto.router)
app.include_router(audio.router)

@app.get("/")
async def home():
    """
    Endpoint raiz para verificar el estado del servidor.
    
    Se utiliza como 'Health Check' para confirmar que la API esta desplegada
    y escuchando peticiones correctamente antes de intentar operaciones complejas.

    :return: Un mensaje de bienvenida indicando que el backend esta activo.
    :rtype: dict
    """
    return{"message" : "Servidor Cadenza Activo. Usa /docs para probar."}