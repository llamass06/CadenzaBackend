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

api_key = os.getenv("GEMINI_API_KEY")

class ObraRequest(BaseModel):
    nombre_obra: str

@router.post("/")
async def generar_contexto_obra(obra: ObraRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="La API Key no está configurada en el servidor.")

    try:
        # Inicializamos el cliente con la nueva sintaxis
        client = genai.Client(api_key=api_key)

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
        
        # Hacemos la petición usando el modelo que tienes disponible
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.4 
            )
        )
        
        return {"contexto": response.text.strip()}
        
    except Exception as e:
        print(f"Error con Gemini: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el contexto con la IA.")