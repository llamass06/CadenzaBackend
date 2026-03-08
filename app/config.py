# CONFIGURACION GLOBAL DEL BACKEND

import os
"""
Para cosas del Sistema Operativo.
Lo uso basicamente para crear las carpetas si no existen y para manejar las rutas
de los archivos (paths) sin lios de barras, para que funcione igual en mi PC y en Linux.
"""

# FICHEROS IMPORTANTES
UPLOAD_DIR = "uploads" # Aqui se guarda lo que sube el usuario
OUTPUT_DIR = "separated" # Aqui es donde demucs deja los dos archivos resultantes (TEMPORAL => Tengo que migrarlo a BBDD)
MODEL_NAME = "htdemucs_6s" # Modelo de IA usado para la manipulacion, conversion y creacion de audios. NO TOCAR A MENOS QUE SE TENGA QUE MIGRAR

# CONCURRENCIA
# Maximo de usuarios que pueden procesar una obra a la vez.
MAX_PROCESOS = 1

# CREACION DE CARPETAS 
# El exist_ok por si ya existe, para que no pete
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)