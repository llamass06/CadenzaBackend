import librosa
"""
Libreria estandar para el analisis de audio y musica.
La usamos para extraer caracteristicas matematicas de la cancion, como el tempo (BPM)
o la duracion, sin necesidad de reproducirla. Es el 'cerebro musical' del backend.
"""

import numpy as np
"""
Libreria para calculo cientifico.
Librosa devuelve los datos del audio como 'arrays' de Numpy (listas de numeros gigantes).
Necesitamos Numpy para manejar estos datos si quisieramos hacer calculos mas complejos.
"""

def analizar_track(file_path: str) -> dict:
    """
    Analiza un archivo de audio para extraer metadatos musicales utiles para el musico.
    
    Utiliza la libreria Librosa para leer la onda de sonido y calcular matematicamente
    el ritmo (BPM) y la duracion total. Esta funcion esta diseñada para ser rapida,
    analizando solo una muestra inicial para el BPM.

    :param file_path: Ruta absoluta o relativa del archivo de audio (.mp3, .wav) a analizar.
    :return: Un diccionario con:
        - 'bpm': El tempo detectado (Beats Per Minute).
        - 'duration': La duracion total en segundos.
        - 'key': (Placeholder) La tonalidad detectada (ej: 'C min').
    """
    print(f"--> [Analisis] Calculando BPM para: {file_path}")
    
    try:
        # 1. CARGA DEL AUDIO (OPTIMIZADA)
        # librosa.load convierte el mp3 en una lista de numeros (y) y nos da la frecuencia de muestreo (sr).
        # Uso 'duration=60' para cargar SOLO el primer minuto. Cargar mas minutos seria irrelevante y costoso
        list_num, frec_muestreo = librosa.load(file_path, duration=60)
        
        # 2. DETECCION DEL TEMPO (BPM)
        # beat_track busca los picos de volumen repetitivos (los golpes fuertes)
        # y calcula la distancia promedio entre ellos para sacar el ritmo.
        # Devuelve el tempo estimado y una lista de 'beats' (que aqui ignoramos con el _).
        tempo, _ = librosa.beat.beat_track(y=list_num, sr=frec_muestreo)
        
        # 3. DETECCION DE DURACION TOTAL
        # get_duration lee la cabecera del archivo para saber cuanto dura exactamente, sin necesidad de decodificar todo el audio (es instantaneo).
        # Con la duracion construire un slider en flutter
        duration = librosa.get_duration(path=file_path)
        
        # 4. LIMPIEZA DE DATOS
        # Librosa devuelve tipos 'numpy.float', que a veces dan problemas al convertirlos a JSON.
        # Los convierfto a 'float' nativo de Python y redondeamos a 1 decimal para que quede bonito.
        bpm_val = round(float(tempo), 1)
        duration_val = round(float(duration), 1)
        
        print(f"<-- [Analisis] BPM: {bpm_val} | Duracion: {duration_val}s") #La duracion es en segundos
        
        return {
            "bpm": bpm_val,
            "duration": duration_val,
            "key": "Nose" # TODO() Se podria hacer un modulo para que detecte la TONALIDAD
        }
        
    except Exception as e:
        # Si algo va mal, ya sea pq el archivo este corrupto o lo q seam se devueve un metronomo en 0, para que el usuario lo ponga a mano.
        print(f"Error en analisis musical: {e}")
        return {"bpm": 0, "duration": 0}