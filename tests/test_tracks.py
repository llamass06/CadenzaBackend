import pytest
from app.database import models
from app.main import app
from app.auth import get_current_user

def test_get_mis_obras_empty(client, session):
    # Mockear el usuario autenticado
    mock_user = models.User(id=1, email="test@example.com", username="testuser")
    
    # Añadir usuario a BBDD en memoria para evitar errores de Foreign Key si los hubiera
    session.add(mock_user)
    session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.get("/api/v1/mis-obras")
    assert response.status_code == 200
    assert response.json() == []
    
    app.dependency_overrides.pop(get_current_user, None)

def test_get_mis_obras_with_data(client, session):
    # Setup de usuario y canciones
    mock_user = models.User(id=1, email="test@example.com", username="testuser")
    session.add(mock_user)
    session.commit()
    
    song1 = models.Song(title="Song 1", bpm=120.0, duration=180.0, owner_id=1, path_backing="test/path.mp3")
    session.add(song1)
    session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.get("/api/v1/mis-obras")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Song 1"
    assert data[0]["bpm"] == 120.0
    
    app.dependency_overrides.pop(get_current_user, None)

def test_delete_obra_success(client, session):
    mock_user = models.User(id=1, email="test@example.com", username="testuser")
    session.add(mock_user)
    session.commit()
    
    song1 = models.Song(title="Song 1", bpm=120.0, duration=180.0, owner_id=1, path_backing="test/path.mp3")
    session.add(song1)
    session.commit()
    song_id = song1.id
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.delete(f"/api/v1/obras/{song_id}")
    assert response.status_code == 200
    assert "eliminada correctamente" in response.json()["message"]
    
    # Verificar que se eliminó de la BD
    deleted_song = session.query(models.Song).filter(models.Song.id == song_id).first()
    assert deleted_song is None
    
    app.dependency_overrides.pop(get_current_user, None)

def test_delete_obra_not_found(client, session):
    mock_user = models.User(id=1, email="test@example.com", username="testuser")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.delete("/api/v1/obras/999")
    assert response.status_code == 404
    assert "no encontrada" in response.json()["detail"].lower()
    
    app.dependency_overrides.pop(get_current_user, None)
