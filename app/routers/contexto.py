"""
Módulo de generación de contexto musicológico mediante IA.

Este módulo expone un endpoint que, dado el nombre de una obra musical,
consulta a la API de Google Gemini para obtener un párrafo de contexto
histórico, biográfico e instrumental sobre dicha obra.

Solo se aceptan obras de música académica (Renacimiento → Contemporánea)
y bandas sonoras originales de cine/videojuegos de corte orquestal o acústico.
Cualquier otro género (pop, rock, reguetón, electrónica...) es rechazado.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai

load_dotenv()

router = APIRouter(
    prefix="/api/contexto",
    tags=["Contexto IA"]
)

# Cargamos la API Key de Gemini desde las variables de entorno
api_key = os.getenv("GEMINI_API_KEY")

class ObraRequest(BaseModel):
    """
    Modelo de datos para la solicitud de contexto de una obra.
    
    Attributes:
        nombre_obra (str): Nombre de la obra musical a analizar (puede incluir autor).
                           Ejemplo: "Requiem de Mozart" o "One-Winged Angel de Nobuo Uematsu".
    """
    nombre_obra: str

@router.post("/")
async def generar_contexto_obra(obra: ObraRequest):
    """
    Genera un párrafo de contexto musicológico para una obra dada usando Gemini.
    
    Este endpoint envía el nombre de la obra a la API de Google Gemini con un
    prompt muy estricto que actúa como un musicólogo experto. El modelo tiene
    instrucciones claras para:
    - No inventar datos biográficos ni fechas.
    - Cubrir únicamente música académica y bandas sonoras orquestales.
    - Devolver un mensaje de error estandarizado si la obra no es identificable
      o pertenece a un género no permitido (pop, rock, etc.).
    
    Args:
        obra (ObraRequest): Objeto con el campo `nombre_obra` que identifica la pieza.
        
    Returns:
        dict: Un diccionario con la clave `contexto` que contiene el párrafo generado
              por la IA en texto plano.
              
    Raises:
        HTTPException:
            - 500 Si la API Key de Gemini no está configurada en el servidor.
            - 500 Si ocurre cualquier otro error durante la comunicación con la API de Gemini.
    """
    if not api_key:
        raise HTTPException(status_code=500, detail="La API Key no está configurada en el servidor.")

    try:
        # Inicializamos el cliente con la API Key cargada desde el entorno
        client = genai.Client(api_key=api_key)

        # Prompt diseñado para comportarse como un musicólogo con reglas estrictas de ámbito
        prompt = f"""
        Actúa como un musicólogo experto y profesor de conservatorio. Analiza la siguiente entrada: "{obra.nombre_obra}".

        INSTRUCCIONES Y REGLAS ESTRICTAS DE ÁMBITO:
        0. NO INVENTES: Tienes estrictamente PROHIBIDO inventar fechas de nacimiento, años, nacionalidades o biografías falsas. Si no tienes datos reales exactos en tu base de conocimiento sobre este compositor y esta obra específica, NO asumas que es música sacra o clásica antigua.
        1. DOMINIO PERMITIDO: Solo puedes analizar música académica (desde el Renacimiento hasta la Contemporánea) y Bandas Sonoras Originales (cine y videojuegos) de corte orquestal, coral o instrumental acústico.
        2. ALERTA DE FALSOS POSITIVOS: Ten en cuenta que muchas bandas sonoras de videojuegos modernos utilizan títulos litúrgicos, en latín o de aspecto religioso. Identifícalas correctamente en su contexto audiovisual contemporáneo en lugar de asumir que son obras sacras antiguas.
        3. DOMINIO PROHIBIDO: Descarta absolutamente cualquier obra de música urbana, pop, rock, reguetón o electrónica de baile.
        4. FORMATO DE ÉXITO: Si identificas la obra claramente dentro del dominio permitido, escribe un único párrafo (mínimo 3 líneas, máximo 10 líneas) detallando su contexto histórico o narrativo, su compositor, tanto datos sobre su vida como su estilo de musica y un detalle técnico o de instrumentación.
        5. FORMATO DE ERROR (CERO INVENTIVA): Si el nombre es genérico (ej. "pista_1", "audio") o pertenece al dominio prohibido, no intentes adivinar. Responde EXACTAMENTE con esta frase:
        "No he podido identificar la obra con precisión dentro del ámbito académico o de bandas sonoras. Por favor, edita el título y el autor en el panel para un análisis correcto."

        Devuelve solo el texto plano, sin formatos ni negritas.
        """
        
        print(f"DEBUG: Enviando a Gemini -> {obra.nombre_obra}")
        
        # Petición al modelo con temperatura baja para respuestas más precisas y conservadoras
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.4  # Valores bajos = respuestas más fiables y menos creativas
            )
        )
        
        return {"contexto": response.text.strip()}
        
    except Exception as e:
        print(f"Error con Gemini: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el contexto con la IA.")