"""
Punto de entrada principal de la aplicación Cadenza Backend.

Este módulo crea y configura la instancia de FastAPI (`app`) que sirve como
núcleo de toda la API. Sus responsabilidades son:
- Inicializar la aplicación con metadatos (título, descripción, versión).
- Configurar el middleware CORS para permitir peticiones desde el frontend.
- Crear las tablas de la base de datos SQLite al arrancar (si no existen).
- Montar la carpeta de archivos estáticos para que los audios sean accesibles por URL.
- Registrar todos los routers de la API con sus prefijos y etiquetas.

Comando de arranque:
    uvicorn app.main:app --reload

Historial de versiones:
    1.0.0 — Separación de audio con Demucs (piano y acompañamiento).
    1.1.0 — Análisis de tempo (BPM) con Librosa para el metrónomo.
    1.1.1 — Validación de formato de archivo en la subida.
    1.2.0 — Base de datos SQLite, registro de usuarios y autenticación JWT.
"""

# FastAPI: framework principal de la API.
# StaticFiles: expone una carpeta del servidor como ruta web pública.
# JSONResponse: permite construir respuestas JSON personalizadas.
# CORSMiddleware: gestiona los permisos de origen cruzado (Cross-Origin Resource Sharing).
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configuración global de rutas y constantes del servidor
from app.config import OUTPUT_DIR

# Routers de la API, cada uno agrupa un conjunto de endpoints relacionados
from app.routers import tracks   # Endpoints de separación y gestión de obras
from app.routers import auth     # Endpoints de registro, verificación y login
from app.routers import contexto # Endpoint de generación de contexto musicológico con Gemini
from app.routers import audio    # Endpoint de subida de audio temporal

# Modelos ORM y motor de BBDD para la creación automática de tablas
from app.database import models
from app.database.database import engine

# --- INSTANCIA PRINCIPAL DE LA APLICACIÓN ---
app = FastAPI(
    title="Cadenza Backend",
    description="""
    API REST del proyecto integrado 'Cadenza'.
    Recibe una obra musical en formato de audio, la procesa con el modelo de IA Demucs
    para separar el acompañamiento del piano, analiza su tempo con Librosa
    y genera un contexto musicológico con la API de Google Gemini.
    """,
    version="1.2.0"
)

# --- CONFIGURACIÓN DE CORS ---
# Lista de orígenes permitidos para hacer peticiones a esta API.
# Solo el frontend de desarrollo (Vite en puerto 5173) está autorizado.
# En producción, aquí iría la URL del dominio del frontend desplegado.
origins = [
    "http://localhost:5173",
    "https://cadenza-frontend-ten.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Necesario para enviar cookies o el header Authorization con el JWT
    allow_methods=["*"],     # Permite todos los métodos HTTP (GET, POST, DELETE, etc.)
    allow_headers=["*"],     # Permite cualquier cabecera, incluido 'Authorization: Bearer <token>'
)

# --- INICIALIZACIÓN DE LA BASE DE DATOS ---
# Crea físicamente las tablas en cadenza.db según los modelos ORM definidos en models.py.
# Si las tablas ya existen, esta instrucción no hace nada (no borra datos).
models.Base.metadata.create_all(bind=engine)

# --- ARCHIVOS ESTÁTICOS ---
# Monta la carpeta OUTPUT_DIR ("separated") en la ruta /files del servidor.
# Esto permite que el frontend acceda a los audios procesados mediante URLs del tipo:
# http://127.0.0.1:8000/files/htdemucs_6s/<carpeta_obra>/no_piano.mp3
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")

# --- REGISTRO DE ROUTERS ---
# Cada router agrupa un conjunto de endpoints. El prefijo se antepone a todas sus rutas.
# Los tags agrupan los endpoints en secciones dentro de la documentación Swagger (/docs).
app.include_router(auth.router, prefix="/api/auth", tags=["Usuarios y Seguridad"])
app.include_router(tracks.router, prefix="/api/v1", tags=["IA y Pistas"])
app.include_router(contexto.router)  # Prefijo definido internamente: /api/contexto
app.include_router(audio.router)     # Prefijo definido internamente: /api/audio

@app.get("/")
async def home():
    """
    Endpoint raíz de verificación del estado del servidor (Health Check).
    
    Permite comprobar de forma rápida que la API está desplegada y respondiendo
    antes de realizar operaciones más complejas. También sirve como punto de
    entrada para herramientas de monitorización.
    
    Returns:
        dict: Mensaje de confirmación indicando que el servidor está activo
              y recordando la URL de la documentación interactiva.
    """
    return {"message": "Servidor Cadenza Activo. Usa /docs para probar."}