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
from app.config import OUTPUT_DIR
from app.routers import tracks

# CONFIGURACION 
"""
Convenio de cambio de versiones:
    -1.0.X => Cuando se arregla un bug pequeño.
    -1.X.0 => Cuando se añade una nueva funcionalidad, pero el resto sigue igual.
    -X.0.0 => Cuando el cambio hace que lo demas deje de funcionalidad (bastante radical btw).
"""
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
    
    """,
    version="1.1.0"
)

# IMPORTANTE (web)
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")
"""
Montar la carpeta separated para que sea accesible por web.
Esto permite que la app descargue los audios resultantes.
"""

# Incluir las rutas (Endpoints)
# Si tuviese mas modulos tipo usuario etc, se ponen aqui
# El prefix="/api" hace que la ruta final sea /api/separar
app.include_router(tracks.router, prefix="/api/v1")

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