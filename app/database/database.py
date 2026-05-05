"""
Módulo de configuración de la base de datos con SQLAlchemy.

Este módulo centraliza la conexión a la base de datos SQLite, define el motor
(Engine), la fábrica de sesiones (SessionLocal) y la clase base de la que
heredan todos los modelos ORM del proyecto (Base).

También expone la función `get_db`, que actúa como dependencia de FastAPI para
proporcionar y cerrar automáticamente una sesión de BBDD por cada petición HTTP.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexión a SQLite.
# El archivo "cadenza.db" se crea automáticamente en la raíz del proyecto
# (el directorio desde donde se ejecuta uvicorn) si no existe.
SQLALCHEMY_DATABASE_URL = "sqlite:///./cadenza.db"

# Motor (Engine): gestiona la conexión física con el archivo de la BBDD.
# 'check_same_thread: False' es obligatorio en SQLite para permitir que
# FastAPI acceda a la BBDD desde múltiples hilos (necesario con async).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fábrica de sesiones: cada llamada a SessionLocal() crea una sesión nueva e
# independiente. autocommit=False exige hacer commit() manualmente para confirmar
# cambios; autoflush=False evita escrituras automáticas antes del commit.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base de la que heredan todos los modelos ORM (tablas de la BBDD).
# SQLAlchemy usará esta base para mapear las clases Python a tablas SQL.
Base = declarative_base()

def get_db():
    """
    Dependencia de FastAPI que proporciona una sesión de base de datos por petición.
    
    Crea una nueva sesión al inicio de cada request y la cierra automáticamente
    al finalizar, tanto si tuvo éxito como si ocurrió un error. Esto garantiza
    que ninguna conexión quede abierta accidentalmente.
    
    Uso típico en un endpoint:
        db: Session = Depends(get_db)
    
    Yields:
        Session: Sesión activa de SQLAlchemy lista para realizar consultas y operaciones.
    """
    db = SessionLocal()
    try:
        yield db  # Cede la sesión al endpoint que la solicita
    finally:
        db.close()  # Se ejecuta siempre, incluso si el endpoint lanza una excepción