## Cadenza Backend - Deconstrucción Orquestal para Pianistas 🎹

Backend del proyecto integrado Cadenza, una herramienta diseñada para estudiantes de piano que permite aislar o eliminar la pista de piano de cualquier obra musical u orquestal utilizando Inteligencia Artificial, y ofrecer un análisis de contexto avanzado.

## 🚀 Estado del Proyecto

Actualmente, el backend es plenamente funcional en producción, gestionando la separación de audio, el análisis musical matemático, la generación de contexto mediante LLMs y sirviendo datos a la aplicación cliente a través de una API RESTful segura.


##  🌟 Características Implementadas

Separación de Pistas con IA: Integración nativa con el modelo Demucs (htdemucs_6s) para realizar un aislamiento quirúrgico del piano respecto al resto del acompañamiento orquestal.

Análisis Físico y Musical (DSP): Uso de Librosa para el cálculo automatizado del tempo (BPM) y la extracción precisa de la duración de la pista.

Inteligencia Artificial Generativa: Integración con la API de Google Gemini para proporcionar contexto histórico, estilístico y técnico sobre la obra subida.

Gestión de Concurrencia y Hardware: Implementación de semáforos asíncronos (asyncio.Semaphore) para proteger la RAM y CPU del servidor, limitando el procesamiento neuronal a 1 pista simultánea.

Gestión de Biblioteca de Usuario: Sistema de almacenamiento en la nube con validación de cuotas (límite establecido de 3 obras por usuario en el plan actual), incluyendo borrado en cascada de archivos físicos y registros.

Autenticación y Seguridad: Sistema completo de registro y login mediante tokens JWT (JSON Web Tokens) y contraseñas hasheadas con Bcrypt.

Suite de Testing Automatizado: Pruebas de integración y unitarias utilizando Pytest, bases de datos SQLite en memoria (:memory:) para aislamiento, y mocking (unittest.mock) de la IA generativa para garantizar eficiencia.

## 🛠️ Stack Tecnológico

    Lenguaje: Python 3.11.9

    Framework Web: FastAPI / Uvicorn

    Motores de IA: Demucs (Facebook Research) + Google Generative AI (Gemini)

    Digital Signal Processing (DSP): Librosa & NumPy

    Manipulación de Audio: FFmpeg

    Base de Datos: SQLite + SQLAlchemy

    Seguridad: Bcrypt + Python-JOSE

    Testing: Pytest + FastAPI TestClient

    Infraestructura: Servidor VPS Linux (Hetzner) + Ngrok (Túneles de red)

## 📡 Despliegue en Producción

El proyecto está diseñado para ser desplegado en un servidor VPS Linux. El flujo de despliegue actual se realiza mediante:

    Sincronización del código mediante git pull en el entorno de producción (Hetzner).

    Ejecución del servidor ASGI (Uvicorn).

    Exposición segura de la API hacia la web app (Vercel) utilizando túneles de red (Ngrok).

## ⚙️ Instalación y Configuración Local

Prerrequisitos:

    Python 3.11.x (Versiones superiores pueden presentar incompatibilidades con las dependencias tensoriales de PyTorch).

    FFmpeg instalado y añadido al PATH del sistema.

    Claves de API válidas (ej. Google Gemini API Key) configuradas en las variables de entorno.

Pasos de arranque:
Bash

1. Clonar el repositorio
git clone https://github.com/llamass06/CadenzaBackend.git
cd CadenzaBackend

2. Crear y activar el entorno virtual (Windows)
python -m venv venv
.\venv\Scripts\Activate

3. Instalar dependencias estándar
pip install -r requirements.txt

4. Instalación de Demucs desde la fuente oficial
pip install -U git+https://github.com/facebookresearch/demucs#egg=demucs

5. Arrancar el servidor de desarrollo
uvicorn app.main:app --reload

## 🔌 Endpoints Principales (API v1)

Documentación interactiva disponible vía Swagger UI en /docs al arrancar el servidor.
Autenticación

    POST /api/auth/token: Endpoint OAuth2. Recibe credenciales (username, password) y devuelve un token JWT.

Motor Híbrido (Audio & IA)

    POST /api/v1/separar: Recibe un archivo de audio (multipart/form-data), ejecuta la red neuronal, calcula el BPM y genera el contexto. Devuelve:
    JSON

    {
        "status": "success",
        "title": "Nocturne Op. 9 No. 2",
        "artist": "Chopin",
        "piano_url": "https://.../files/piano.mp3",
        "backing_url": "https://.../files/no_piano.mp3",
        "bpm": 132.0,
        "contexto": "El Nocturno Op. 9 No. 2 es una obra romántica que destaca por..."
    }

Gestión de Biblioteca

    GET /api/v1/mis-obras: Devuelve el array de obras procesadas pertenecientes al usuario autenticado (con validación de token).

    DELETE /api/v1/obras/{id}: Elimina de forma segura los metadatos de la base de datos y los archivos físicos del servidor para liberar espacio.

## 🚧 En Desarrollo (Futuras Iteraciones)

    ⏳ Interfaz de sincronización de luces (Hardware IoT) en caso de que el dispositivo cliente disponga de ellas.

    ⏳ Generación automática de partituras dinámicas en base a la transcripción de la obra procesada.
    
    ⏳Pagina de ajustes.

    ⏳ Chatbot.

Desarrollado por Álvaro Llamas Martín - Proyecto Integrado de 2º DAM.
