"""
Módulo de modelos ORM de la base de datos.

Define las tablas de la aplicación usando clases Python mapeadas a SQLite
mediante SQLAlchemy. Cada clase hereda de `Base` (definida en database.py)
y representa una tabla con sus columnas y relaciones.

Tablas definidas:
- User: Almacena los usuarios registrados y su estado de verificación.
- Song: Almacena las obras procesadas, sus metadatos y la ruta de sus archivos de audio.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    """
    Tabla 'users': representa a un usuario registrado en la aplicación.
    
    Attributes:
        id (int): Clave primaria, generada automáticamente.
        email (str): Correo electrónico único del usuario. Se usa como identificador de login.
        username (str): Nombre visible del usuario dentro de la aplicación.
        hashed_password (str): Contraseña encriptada con bcrypt. Nunca se almacena en texto plano.
        created_at (datetime): Fecha y hora de registro, establecida automáticamente al crear el registro.
        is_verified (bool): Indica si el usuario ha verificado su correo. Hasta que sea True, no puede iniciar sesión.
        verification_token (str | None): Token único enviado por correo para activar la cuenta. 
                                         Se pone a None una vez verificado.
        songs (list[Song]): Relación ORM con todas las obras que pertenecen a este usuario.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)         # Único e indexado para búsquedas rápidas en el login
    username = Column(String)
    hashed_password = Column(String)                        # Siempre se guarda el hash, nunca la contraseña real
    created_at = Column(DateTime, default=datetime.utcnow)  # Se rellena automáticamente al crear el usuario

    # Relación 1:N — Un usuario puede tener muchas canciones.
    # back_populates="owner" enlaza con el campo 'owner' definido en la clase Song.
    songs = relationship("Song", back_populates="owner")
    
    # Campos de verificación de correo electrónico
    is_verified = Column(Boolean, default=False)            # False por defecto hasta que el usuario active su cuenta
    verification_token = Column(String, nullable=True)      # Se elimina (None) tras la verificación exitosa


class Song(Base):
    """
    Tabla 'songs': representa una obra musical procesada por la IA.
    
    Cada registro corresponde a una subida de audio por parte de un usuario.
    Almacena los metadatos de la obra, las rutas a los archivos de audio generados
    por Demucs y el texto de contexto musicológico generado por Gemini.
    
    Attributes:
        id (int): Clave primaria, generada automáticamente.
        title (str): Título de la obra introducido por el usuario.
        artist (str): Nombre del compositor o intérprete (puede ser None si no se proporcionó).
        contexto (str | None): Párrafo de contexto histórico/musical generado por Gemini. 
                               Puede ser None si la IA no pudo identificar la obra.
        path_piano (str | None): Ruta relativa al archivo piano.mp3 dentro del OUTPUT_DIR.
                                 Actualmente siempre None, ya que el archivo se elimina tras la separación.
        path_backing (str): Ruta relativa al archivo no_piano.mp3 (el acompañamiento) dentro del OUTPUT_DIR.
        bpm (float): Tempo de la obra en pulsaciones por minuto, analizado automáticamente.
        duration (float): Duración total del audio en segundos.
        owner_id (int): Clave foránea que referencia al usuario propietario de esta obra.
        owner (User): Relación ORM inversa que permite acceder al objeto User desde una Song.
    """
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)                      # Indexado para permitir búsquedas por título
    artist = Column(String)
    contexto = Column(String, nullable=True)                # Generado por Gemini; puede ser None si falla la IA
    
    # Rutas relativas a los archivos físicos en el servidor (dentro de OUTPUT_DIR)
    path_piano = Column(String)                             # Siempre None: el piano.mp3 se borra tras la separación
    path_backing = Column(String)                           # Ruta al acompañamiento (no_piano.mp3)
    
    # Metadatos musicales analizados automáticamente por librosa
    bpm = Column(Float)
    duration = Column(Float)
    
    # Clave foránea que vincula cada obra con su usuario propietario
    owner_id = Column(Integer, ForeignKey("users.id"))

    # Relación inversa: permite acceder a song.owner para obtener el objeto User completo
    owner = relationship("User", back_populates="songs")