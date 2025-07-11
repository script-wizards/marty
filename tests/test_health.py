import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Test that the /health endpoint returns a 200 status code"""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_correct_json():
    """Test that the /health endpoint returns the correct JSON response"""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_endpoint_content_type():
    """Test that the /health endpoint returns JSON content type"""
    response = client.get("/health")
    assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_health_endpoint_async():
    """Test the health endpoint in async mode"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
