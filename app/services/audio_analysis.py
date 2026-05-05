"""
Módulo de análisis musical de archivos de audio.

Utiliza la librería Librosa para extraer metadatos musicales de forma automática
a partir de un archivo de audio, sin necesidad de reproducirlo. Actualmente
extrae el tempo (BPM) y la duración total.

Librerías utilizadas:
- librosa: Librería estándar de Python para análisis de audio y música.
           Convierte el archivo en señales numéricas y aplica algoritmos de
           procesamiento de señal para detectar el tempo y la duración.
- numpy:   Librosa trabaja internamente con arrays de NumPy (representaciones
           numéricas de la señal de audio). Se importa para gestionar esos
           datos si se necesitan cálculos adicionales en el futuro.
"""

import librosa
import numpy as np

def analizar_track(file_path: str) -> dict:
    """
    Analiza un archivo de audio y extrae sus metadatos musicales principales.
    
    Para optimizar el rendimiento, solo carga el primer minuto del archivo
    para la detección de BPM (suficiente para obtener un tempo representativo),
    mientras que la duración total se lee directamente desde la cabecera del
    archivo, sin necesidad de decodificarlo entero.
    
    Args:
        file_path (str): Ruta al archivo de audio a analizar (.mp3, .wav, .flac, etc.).
        
    Returns:
        dict: Un diccionario con los siguientes campos:
            - 'bpm' (float): Tempo estimado de la obra en pulsaciones por minuto,
                             redondeado a 1 decimal. Devuelve 0 si el análisis falla.
            - 'duration' (float): Duración total del audio en segundos, redondeada
                                  a 1 decimal. Devuelve 0 si el análisis falla.
            - 'key' (str): Tonalidad de la obra. Actualmente es un placeholder ('TODO');
                           se podría implementar con el análisis cromático de Librosa.
    """
    print(f"--> [Analisis] Calculando BPM para: {file_path}")
    
    try:
        # 1. CARGA DEL AUDIO (OPTIMIZADA)
        # librosa.load decodifica el archivo de audio en una señal numérica (y) y devuelve
        # la frecuencia de muestreo (sr). Limitamos a los primeros 60 segundos para evitar
        # cargar archivos largos enteros en memoria, ya que el tempo se puede estimar con ese fragmento.
        list_num, frec_muestreo = librosa.load(file_path, duration=60)
        
        # 2. DETECCIÓN DEL TEMPO (BPM)
        # beat_track localiza los picos de energía rítmica en la señal y calcula
        # la distancia promedio entre ellos para estimar el tempo.
        # El segundo valor devuelto (posiciones exactas de los beats) se descarta con _.
        tempo, _ = librosa.beat.beat_track(y=list_num, sr=frec_muestreo)
        
        # 3. DETECCIÓN DE DURACIÓN TOTAL
        # get_duration lee directamente la cabecera del archivo sin decodificar el audio completo,
        # lo que lo hace prácticamente instantáneo independientemente de la duración de la obra.
        duration = librosa.get_duration(path=file_path)
        
        # 4. CONVERSIÓN Y LIMPIEZA DE TIPOS
        # Librosa devuelve valores de tipo numpy.float64, que pueden causar errores de
        # serialización al convertirlos a JSON. Se convierten a float nativo de Python
        # y se redondean a 1 decimal para una presentación limpia en el frontend.
        bpm_val = round(float(tempo), 1)
        duration_val = round(float(duration), 1)
        
        print(f"<-- [Analisis] BPM: {bpm_val} | Duracion: {duration_val}s")
        
        return {
            "bpm": bpm_val,
            "duration": duration_val,
            "key": "TODO"  # TODO: implementar detección de tonalidad con análisis cromático (librosa.feature.chroma_cqt)
        }
        
    except Exception as e:
        # Si el archivo está corrupto o el análisis falla, se devuelven valores en 0
        # para que el usuario pueda editarlos manualmente desde el panel.
        print(f"Error en analisis musical: {e}")
        return {"bpm": 0, "duration": 0}