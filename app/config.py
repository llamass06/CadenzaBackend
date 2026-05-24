"""
Módulo de configuración global del backend.

Define las constantes y rutas compartidas por todos los módulos de la aplicación.
Centralizar estos valores aquí facilita el mantenimiento: si se necesita cambiar
un directorio o el modelo de IA, solo hay que modificarlo en este archivo.

Este módulo también se encarga de crear los directorios necesarios al arrancar
el servidor, garantizando que la estructura de carpetas siempre esté lista antes
de que llegue cualquier petición.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno globalmente
load_dotenv()

# --- DIRECTORIOS DE ARCHIVOS ---

# Carpeta donde se almacenan temporalmente los archivos de audio subidos por el usuario
# antes de ser procesados por Demucs.
UPLOAD_DIR = "uploads"

# Carpeta donde Demucs deposita las pistas separadas (piano.mp3 y no_piano.mp3) tras
# el procesamiento. El archivo piano.mp3 se elimina automáticamente en tracks.py.
OUTPUT_DIR = "separated"

# --- MODELO DE IA ---

# Nombre del modelo de Demucs utilizado para la separación de fuentes.
# 'htdemucs_6s' es la versión de 6 fuentes (voz, batería, bajo, piano, guitarra, otros)
# aunque aquí solo extraemos piano y acompañamiento con --two-stems.
# IMPORTANTE: No cambiar este valor sin verificar que el nuevo modelo esté instalado
# en el servidor y que su nombre de carpeta de salida coincida con el usado en tracks.py.
MODEL_NAME = "htdemucs_6s"

# --- CONCURRENCIA ---

# Número máximo de procesos de Demucs que pueden ejecutarse simultáneamente.
# Se mantiene en 1 para evitar desbordamiento de RAM en el servidor de despliegue (4 GB).
# Aumentar este valor solo si el servidor dispone de más memoria y núcleos disponibles.
MAX_PROCESOS = 1

# --- REGLAS DE NEGOCIO ---
MAX_OBRAS = 3

# --- RUTAS Y URLs ---
BASE_URL = os.getenv("BASE_URL")

# --- INICIALIZACIÓN DE DIRECTORIOS ---

# Se crean los directorios al importar este módulo (al arrancar el servidor).
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)