import pytest
from unittest.mock import patch

def test_contexto_success(client):
    # Mockear la respuesta de la IA para que no gaste créditos de Gemini
    with patch("app.routers.contexto.genai.Client") as mock_client:
        mock_instance = mock_client.return_value
        # Configuramos el mock de models.generate_content
        mock_response = mock_instance.models.generate_content.return_value
        mock_response.text = "El Requiem en Re menor, K. 626, es una misa de Wolfgang Amadeus Mozart..."
        
        response = client.post(
            "/api/contexto/",
            json={"nombre_obra": "Requiem de Mozart"}
        )
        
        assert response.status_code == 200
        assert "contexto" in response.json()
        assert "Mozart" in response.json()["contexto"]

def test_contexto_no_api_key(client):
    # Probar el fallo cuando no hay API_KEY
    with patch("app.routers.contexto.api_key", None):
        response = client.post(
            "/api/contexto/",
            json={"nombre_obra": "Sinfonia No. 9 de Beethoven"}
        )
        assert response.status_code == 500
        assert "no está configurada" in response.json()["detail"]
