"""
Módulo de generación de contexto musicológico mediante IA.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.gemini_service import consultar_contexto_gemini

router = APIRouter(
    prefix="/api/contexto",
    tags=["Contexto IA"]
)

class ObraRequest(BaseModel):
    nombre_obra: str

@router.post("/")
async def generar_contexto_obra(obra: ObraRequest):
    contexto = await consultar_contexto_gemini(obra.nombre_obra)
    return {"contexto": contexto}