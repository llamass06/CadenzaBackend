from pydantic import BaseModel
from typing import List, Optional

# --- 1. SCHEMAS PARA CANCIONES ---

# Datos base que siempre tienen las canciones (comunes)
class SongBase(BaseModel):
    title: str
    bpm: float
    duration: float
    contexto: Optional[str] = None

# Datos necesarios para crear una cancion (lo usamos internamente al procesar)
class SongCreate(SongBase):
    path_piano: str
    path_backing: str

# Datos que devolvemos al leer una cancion (Output)
class Song(SongBase):
    id: int
    owner_id: int
    
    # Config para que Pydantic sepa leer los modelos de SQLAlchemy (BBDD)
    class Config:
        #orm_mode = True
        from_attributes = True

# --- 2. SCHEMAS PARA USUARIOS ---

# Datos base del usuario
class UserBase(BaseModel):
    email: str
    username: str

# Datos para registrarse (Input) 
class UserCreate(UserBase):
    password: str 

# Datos para devolver info del usuario (Output) 
class User(UserBase):
    id: int
    # is_active: bool = True # Puedes descomentarlo si añades este campo en models.py
    songs: List[Song] = [] # Incluimos la lista de sus canciones procesadas

    class Config:
        orm_mode = True

# --- 3. SCHEMAS PARA EL TOKEN (LOGIN) ---

# Lo que devolvemos cuando el login es correcto
class Token(BaseModel):
    access_token: str
    token_type: str

# Datos que lleva el token por dentro (payload)
class TokenData(BaseModel):
    username: Optional[str] = None