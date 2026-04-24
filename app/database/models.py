from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    hashed_password = Column(String) # Clave hasheada
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación: Un usuario tiene muchas canciones
    # 'Song' es el nombre de la clase, back_populates conecta con el campo 'owner' en Song
    songs = relationship("Song", back_populates="owner")

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    
    artist = Column(String)
    
    contexto = Column(String, nullable=True)
    
    # Rutas a los archivos físicos en el servidor
    path_piano = Column(String)
    path_backing = Column(String)
    
    # Metadatos musicales
    bpm = Column(Float)
    duration = Column(Float)
    
    # Clave Foránea (Link al usuario que la subió)
    owner_id = Column(Integer, ForeignKey("users.id"))

    # Relación inversa
    owner = relationship("User", back_populates="songs")