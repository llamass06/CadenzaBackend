"""
Módulo del servicio de IA de Gemini.

Encapsula la comunicación con la API de Google Gemini para obtener 
contexto musicológico.
"""
import os
from google import genai
from fastapi import HTTPException

# Cargamos la API Key desde el entorno (asegúrate de que load_dotenv() se llame antes o en main)
api_key = os.getenv("GEMINI_API_KEY")

async def consultar_contexto_gemini(title: str, artist: str = None) -> str:
    """
    Consulta a Gemini el contexto de la obra.
    Maneja internamente la lógica de la API de Google.
    """
    if not api_key:
        print("La API Key de Gemini no está configurada.")
        return "Información no disponible por falta de configuración del servidor."

    nombre_obra = f"{title} de {artist}" if artist else title

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Actúa como un musicólogo experto y profesor de conservatorio. Analiza la siguiente entrada: "{nombre_obra}".

        INSTRUCCIONES Y REGLAS ESTRICTAS DE ÁMBITO:
        0. NO INVENTES: Tienes estrictamente PROHIBIDO inventar fechas de nacimiento, años, nacionalidades o biografías falsas. Si no tienes datos reales exactos en tu base de conocimiento sobre este compositor y esta obra específica, NO asumas que es música sacra o clásica antigua.
        1. TOLERANCIA A ERRORES (FUZZY MATCHING): El usuario puede haber escrito el título o el autor con faltas de ortografía, errores tipográficos o nombres incompletos (ej. "claro de luan" en lugar de "Clair de Lune", o "Chopen" en lugar de "Chopin"). Debes inferir inteligentemente de qué obra se trata antes de rechazarla.
        2. DOMINIO PERMITIDO: Solo puedes analizar música académica (desde el Renacimiento hasta la Contemporánea) y Bandas Sonoras Originales (cine y videojuegos) de corte orquestal, coral o instrumental acústico.
        3. ALERTA DE FALSOS POSITIVOS: Ten en cuenta que muchas bandas sonoras de videojuegos modernos utilizan títulos litúrgicos, en latín o de aspecto religioso. Identifícalas correctamente en su contexto audiovisual contemporáneo en lugar de asumir que son obras sacras antiguas.
        4. DOMINIO PROHIBIDO: Descarta absolutamente cualquier obra de música urbana, pop, rock, reguetón o electrónica de baile.
        5. FORMATO DE ÉXITO: Si identificas o deduces la obra correctamente dentro del dominio permitido, escribe un único párrafo (mínimo 3 líneas, máximo 10 líneas) detallando su contexto histórico o narrativo, su compositor, tanto datos sobre su vida como su estilo de musica y un detalle técnico o de instrumentación. Asegúrate de escribir el nombre real y correcto del autor y la obra al principio del texto.
        6. FORMATO DE ERROR (CERO INVENTIVA): Si el nombre es irreconocible incluso intentando deducirlo, o pertenece al dominio prohibido, no intentes adivinar. Responde EXACTAMENTE con esta frase:
        "No he podido identificar la obra con precisión dentro del ámbito académico o de bandas sonoras. Por favor, edita el título y el autor en el panel para un análisis correcto."

        Devuelve solo el texto plano, sin formatos ni negritas.
        """
        
        print(f"DEBUG: Enviando a Gemini -> {nombre_obra}")
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.4
            )
        )
        return response.text.strip()
        
    except Exception as e:
        print(f"Error generando contexto IA: {e}")
        return "Información no disponible."
