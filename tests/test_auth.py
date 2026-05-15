import pytest
from app.database import models
from app.auth import get_password_hash

def test_register_user_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    assert "Usuario creado" in response.json()["message"]

def test_register_user_duplicate(client, session):
    # Crear un usuario primero
    hashed_password = get_password_hash("password123")
    user = models.User(email="test@example.com", username="testuser", hashed_password=hashed_password, is_verified=True)
    session.add(user)
    session.commit()

    # Intentar registrar el mismo email
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser2", "password": "password123"}
    )
    assert response.status_code == 400
    assert "ya está registrado" in response.json()["detail"]

def test_login_success(client, session):
    # Crear usuario verificado
    hashed_password = get_password_hash("password123")
    user = models.User(email="test@example.com", username="testuser", hashed_password=hashed_password, is_verified=True)
    session.add(user)
    session.commit()

    # Intentar login
    response = client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "password123"} # OAuth2PasswordRequestForm usa form data
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_unverified(client, session):
    # Crear usuario NO verificado
    hashed_password = get_password_hash("password123")
    user = models.User(email="test@example.com", username="testuser", hashed_password=hashed_password, is_verified=False)
    session.add(user)
    session.commit()

    # Intentar login
    response = client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 403
    assert "aún no está verificada" in response.json()["detail"]

def test_login_wrong_password(client, session):
    hashed_password = get_password_hash("password123")
    user = models.User(email="test@example.com", username="testuser", hashed_password=hashed_password, is_verified=True)
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"]
