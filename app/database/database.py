from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ruta de la base de datos.
# "sqlite:///./cadenza.db" creara el archivo en la carpeta raiz de tu proyecto (donde ejecutas uvicorn)
SQLALCHEMY_DATABASE_URL = "sqlite:///./cadenza.db"

# Configuracion del motor (Engine)
# 'check_same_thread': False es necesario solo para SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fabrica de sesiones (Cada peticion tendra su propia sesion)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos (tablas)
Base = declarative_base()

# Dependencia: Funcion que usaran los Endpoints para conectarse
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()