"""
Módulo de separación de fuentes de audio mediante Demucs (IA).

Este módulo actúa como puente entre el backend de Python y el modelo de IA
Demucs, ejecutándolo como un subproceso de terminal. Demucs es un modelo de
deep learning desarrollado por Meta que separa las fuentes de una mezcla de audio
(en este caso, piano y acompañamiento) en archivos independientes.

El comando se lanza con parámetros específicamente ajustados para funcionar
dentro de los límites de memoria del servidor de despliegue (4 GB de RAM en Google Cloud).
"""

import subprocess
from app.config import MODEL_NAME, OUTPUT_DIR

def ejecutar_demucs(file_path):
    """
    Lanza el proceso de separación de audio de Demucs como subproceso del sistema.
    
    Construye y ejecuta el comando de Demucs con una configuración optimizada
    para entornos con recursos limitados. Separa el audio de entrada en dos
    pistas: 'piano.mp3' y 'no_piano.mp3', guardándolas en OUTPUT_DIR.
    
    Nota: El archivo piano.mp3 resultante es eliminado posteriormente por el
    endpoint /separar de tracks.py, ya que la aplicación solo utiliza el acompañamiento.
    
    Args:
        file_path (str): Ruta absoluta o relativa al archivo de audio de entrada a procesar.
        
    Returns:
        bool: True si Demucs completó la separación con éxito, False si ocurrió algún error.
    """
    
    # Configuración del comando ajustada para servidores con recursos limitados (4 GB de RAM)
    comando = [
        "demucs",
        "-n", MODEL_NAME,           # Modelo de IA a usar (configurado en app.config)
        file_path,                  # Archivo de entrada a separar
        "-o", OUTPUT_DIR,           # Directorio de salida donde se guardan las pistas separadas
        "--two-stems", "piano",     # Modo de separación: solo genera piano.mp3 y no_piano.mp3 (ahorra tiempo y espacio)
        "--mp3",                    # Formato de salida MP3 en lugar de WAV
        "--mp3-bitrate", "320",     # Máxima calidad de audio (320 kbps)
        "--shifts", "0",            # Desactiva las pasadas de limpieza de ruido; con 1+ mejora la calidad pero multiplica el tiempo de proceso
        "--overlap", "0.25",        # Solapamiento entre segmentos para evitar artefactos audibles en los cortes
        "--segment", "7",           # Tamaño de segmento en segundos; el máximo seguro es 7 (el modelo acepta hasta ~7.8 pero solo enteros)
        "--clip-mode", "rescale",   # Evita distorsión por clipping reescalando la señal si supera el límite
        "-j", "0"                   # Deshabilita el paralelismo interno para no desbordar la RAM disponible
    ]
    
    try:
        # check=True lanza CalledProcessError automáticamente si Demucs retorna un código de error
        subprocess.run(comando, check=True)
        print(f"<-- [IA] Terminado correctamente.")
        return True
    except subprocess.CalledProcessError as ex:
        print(f"Error en Demucs: {ex}")
        return False