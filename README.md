Cadenza Backend - Deconstrucción Orquestal para Pianistas 🎹

Backend del proyecto integrado Cadenza, una herramienta diseñada para estudiantes de piano que permite aislar o eliminar la pista de piano de cualquier obra musical u orquestal utilizando Inteligencia Artificial.

🚀 Estado del Proyecto

Actualmente, el backend es plenamente funcional en cuanto al procesamiento de audio y análisis musical.

Características Implementadas:

✅ Separación de Pistas con IA: Integración con el modelo Demucs (htdemucs_6s) para aislar el piano del resto del acompañamiento.

✅ Análisis Musical: Cálculo del tempo (BPM) y la duración de la pista utilizando Librosa.

✅ Gestión de Concurrencia: Implementación de semáforos asíncronos (asyncio.Semaphore) para proteger el hardware del servidor limitando el procesamiento a 1 pista simultánea.

✅ API RESTful: Desarrollada con FastAPI para la comunicación fluida con la futura app móvil.

🚧 En Desarrollo (WIP):

⏳ Base de Datos (BBDD): Migración del guardado temporal de archivos a un sistema persistente (SQLite/SQLAlchemy) para registrar el historial de cada usuario y relacionarlo con sus audios.

⏳ Autenticación y Seguridad: Implementación de un sistema de registro y login de usuarios mediante tokens JWT (JSON Web Tokens).

🛠️ Stack Tecnológico

Lenguaje: Python 3.11.9

Framework Web: FastAPI / Uvicorn

Motor de IA (Source Separation): Demucs (Facebook Research)

Análisis de Señal: Librosa & NumPy

Manipulación de Audio: FFmpeg

⚙️ Instalación y Configuración Local

Prerrequisitos

Python 3.11.x (Versiones superiores pueden dar problemas con librerías tensoriales).

FFmpeg instalado y configurado en las variables de entorno (PATH) del sistema.

Git.

Pasos para desplegar

Clonar el repositorio:

git clone [https://github.com/TU-USUARIO/cadenza-backend.git](https://github.com/TU-USUARIO/cadenza-backend.git)
cd cadenza-backend


Crear y activar el entorno virtual:

# En Windows
python -m venv venv
.\venv\Scripts\Activate


Instalar dependencias:

pip install --upgrade pip
pip install fastapi uvicorn python-multipart librosa
pip install "numpy<2"
# Instalación de Demucs desde la fuente oficial
pip install -U git+[https://github.com/facebookresearch/demucs#egg=demucs](https://github.com/facebookresearch/demucs#egg=demucs)


Arrancar el servidor de desarrollo:

uvicorn app.main:app --reload


El servidor estará escuchando en http://127.0.0.1:8000.

📡 Endpoints Principales (API v1)

Puedes probar la API directamente usando Swagger UI navegando a http://127.0.0.1:8000/docs.

GET /

Descripción: Health check para comprobar que el servidor está online.

POST /api/v1/separar

Descripción: Recibe un archivo de audio, ejecuta la red neuronal para separarlo y devuelve las URLs de descarga y los metadatos musicales.

Body: multipart/form-data con la clave file.

Respuesta Exitosa (JSON):

{
    "status": "success",
    "song_name": "nombre_cancion",
    "piano_url": "[http://127.0.0.1:8000/files/htdemucs_6s/nombre_cancion/piano.mp3](http://127.0.0.1:8000/files/htdemucs_6s/nombre_cancion/piano.mp3)",
    "backing_url": "[http://127.0.0.1:8000/files/htdemucs_6s/nombre_cancion/no_piano.mp3](http://127.0.0.1:8000/files/htdemucs_6s/nombre_cancion/no_piano.mp3)",
    "bpm": 120.5,
    "duration": 185.2
}


📁 Estructura del Proyecto

MusicAppBackend/
├── uploads/                    # Recepción de archivos temporales (ignorados en git)
├── separated/                  # Pistas procesadas por la IA (ignorados en git)
├── app/                        # Código fuente del servidor
│   ├── config.py               # Variables globales
│   ├── main.py                 # Core de FastAPI
│   ├── routers/                # Endpoints (tracks.py)
│   └── services/               # Lógica de IA y análisis (ai_separation, audio_analysis)
├── .gitignore                  
└── README.md                   


Desarrollado por Álvaro Llamas Martín para el Proyecto Integrado de 2º DAM.