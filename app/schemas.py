"""
Módulo de schemas de validación y serialización con Pydantic.

Los schemas definen la forma (shape) de los datos que entran y salen de la API.
Pydantic los usa para validar automáticamente los datos recibidos en cada petición
y para serializar las respuestas antes de enviarlas al cliente.

A diferencia de los modelos ORM (models.py), que representan las tablas de la BBDD,
estos schemas representan los contratos de datos de la API (lo que el cliente
puede enviar y lo que la API puede devolver).

Organización:
    1. Schemas de Canciones (Song): SongBase → SongCreate / Song
    2. Schemas de Usuarios (User): UserBase → UserCreate / User
    3. Schemas de Token (JWT): Token / TokenData
"""

from pydantic import BaseModel
from typing import List, Optional

# =============================================================================
# 1. SCHEMAS PARA CANCIONES
# =============================================================================

class SongBase(BaseModel):
    """
    Campos comunes a todas las representaciones de una canción.
    
    Actúa como base de la que heredan SongCreate y Song para evitar duplicar
    la definición de los campos compartidos.
    
    Attributes:
        title (str): Título de la obra musical.
        bpm (float): Tempo de la obra en pulsaciones por minuto.
        duration (float): Duración total del audio en segundos.
        contexto (Optional[str]): Párrafo de contexto musicológico generado por Gemini.
                                   Puede ser None si la IA no identificó la obra.
    """
    title: str
    bpm: float
    duration: float
    contexto: Optional[str] = None

class SongCreate(SongBase):
    """
    Schema de entrada para la creación interna de una canción (uso interno del servidor).
    
    Extiende SongBase añadiendo las rutas de los archivos de audio generados por Demucs.
    No se usa directamente como body de ningún endpoint público; la creación se gestiona
    a través de un Form en el endpoint /separar.
    
    Attributes:
        path_piano (str): Ruta relativa al archivo piano.mp3 dentro de OUTPUT_DIR.
        path_backing (str): Ruta relativa al archivo no_piano.mp3 dentro de OUTPUT_DIR.
    """
    path_piano: str
    path_backing: str

class Song(SongBase):
    """
    Schema de salida para devolver los datos de una canción al cliente.
    
    Incluye los campos de SongBase más los identificadores generados por la BBDD.
    La clase Config con `from_attributes = True` permite a Pydantic leer directamente
    los atributos de un objeto ORM de SQLAlchemy (en lugar de requerir un diccionario).
    
    Attributes:
        id (int): Identificador único de la canción en la base de datos.
        owner_id (int): ID del usuario propietario de esta canción.
    """
    id: int
    owner_id: int
    
    class Config:
        # Necesario para que Pydantic pueda leer objetos ORM de SQLAlchemy directamente.
        # Equivale al antiguo orm_mode = True de Pydantic v1.
        from_attributes = True


# =============================================================================
# 2. SCHEMAS PARA USUARIOS
# =============================================================================

class UserBase(BaseModel):
    """
    Campos comunes a todas las representaciones de un usuario.
    
    Attributes:
        email (str): Correo electrónico del usuario (usado como identificador de login).
        username (str): Nombre visible del usuario dentro de la aplicación.
    """
    email: str
    username: str

class UserCreate(UserBase):
    """
    Schema de entrada para el registro de un nuevo usuario (POST /api/auth/register).
    
    Extiende UserBase añadiendo la contraseña en texto plano, que será hasheada
    por el servidor antes de almacenarse. Nunca se devuelve al cliente.
    
    Attributes:
        password (str): Contraseña en texto plano introducida por el usuario.
    """
    password: str

class User(UserBase):
    """
    Schema de salida con la información pública del usuario.
    
    Incluye los campos de UserBase más el ID y la lista de sus canciones.
    Nunca expone la contraseña (hashed o no).
    
    Attributes:
        id (int): Identificador único del usuario en la base de datos.
        songs (List[Song]): Lista de canciones procesadas que pertenecen al usuario.
    """
    id: int
    songs: List[Song] = []  # Lista vacía por defecto si el usuario aún no tiene obras

    class Config:
        orm_mode = True  # Compatibilidad con Pydantic v1 para leer objetos ORM


# =============================================================================
# 3. SCHEMAS PARA EL TOKEN DE AUTENTICACIÓN (JWT)
# =============================================================================

class Token(BaseModel):
    """
    Schema de salida del endpoint de login (POST /api/auth/token).
    
    Contiene el token JWT generado tras un login exitoso, listo para ser
    almacenado por el cliente y enviado en el header Authorization de futuras peticiones.
    
    Attributes:
        access_token (str): El token JWT firmado.
        token_type (str): Tipo de token, siempre "bearer" en este sistema.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Schema que representa el payload interno decodificado de un token JWT.
    
    Se usa para tipar los datos extraídos del token al validarlo en `get_current_user`.
    
    Attributes:
        username (Optional[str]): Email del usuario extraído del campo 'sub' del token.
                                   Puede ser None si el token no contiene este campo.
    """
    username: Optional[str] = None