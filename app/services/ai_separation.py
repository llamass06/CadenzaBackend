import subprocess 
"""
Para ejecutar comandos de terminal.
Es el puente entre mi codigo y la IA. Lo uso para lanzar el comando de 'demucs'
desde aqui dentro, igual que si lo escribiera yo a mano en la consola.
"""
from app.config import MODEL_NAME, OUTPUT_DIR

def ejecutar_demucs(file_path):
    """
    Funcion que lanza el comando de la IA.
    
    :param file_path: Ruta de donde se coje el audio y se procesa.
    """
    
    # COMANDO OPTIMIZADO PARA MI PORTATIL => Si tuviese un ordenador de la NASA lo mismo lo potenciaba pero me da que no.
    comando = [
        "demucs",
        "-n", MODEL_NAME,
        file_path,
        "-o", OUTPUT_DIR,         # Donde se guarda
        "--two-stems", "piano",   # Solo saco Piano y Acompañamiento (ahorra espacio)
        "--mp3",                  # Salida en MP3
        "--mp3-bitrate", "320",   # Calidad maxima
        "--shifts", "0",          # 2 pasadas para limpiar ruido (tarda un poco mas pero suena mejor), para pruebas lo pongo en 0 q sino tarda la vida
        "--overlap", "0.25",      # Para que no se noten cortes en el audio
        "--segment", "7",       # Segmento seguro para que no falle la memoria (MAX => 7.8 pero solo admite enteros)
        "--clip-mode", "rescale", # Para evitar que el audio distorsione
        "-j", "0"                 # Uso toda la CPU disponible
    ]
    
    try:
        subprocess.run(comando, check=True)
        print(f"<-- [IA] Terminado correctamente.")
        return True
    except subprocess.CalledProcessError as ex:
        print(f"Error en Demucs: {ex}")
        return False