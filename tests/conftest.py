import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.database import Base, get_db
from app.auth import get_current_user
from app.database import models

# Configuración de base de datos en memoria para los tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def session():
    """
    Crea una nueva base de datos para cada test y la destruye al finalizar.
    Proporciona una sesión de SQLAlchemy limpia.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(session):
    """
    Proporciona un TestClient de FastAPI configurado para usar
    la base de datos de pruebas (en memoria).
    """
    def override_get_db():
        try:
            yield session
        finally:
            pass # La sesión se cierra en el fixture `session`

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
