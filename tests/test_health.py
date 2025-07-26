from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Test that the /health endpoint returns a 200 status code"""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_enhanced_json():
    """Test that the /health endpoint returns the enhanced JSON response"""
    response = client.get("/health")
    data = response.json()

    # Check required fields
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
    assert "database" in data
    assert "environment" in data

    # Check database status
    assert data["database"]["status"] == "ok"
    assert data["database"]["type"] == "sqlite"

    # Check timestamp format (ISO format)
    assert "T" in data["timestamp"]
    assert data["timestamp"].endswith("Z") or "+" in data["timestamp"]

    # Check environment
    assert data["environment"] in ["dev", "stage", "prod", "test"]


def test_health_endpoint_content_type():
    """Test that the /health endpoint returns JSON content type"""
    response = client.get("/health")
    assert response.headers["content-type"] == "application/json"


def test_health_endpoint_database_info():
    """Test that the health endpoint includes database information"""
    response = client.get("/health")
    data = response.json()

    assert "database" in data
    assert isinstance(data["database"], dict)
    assert "status" in data["database"]
    assert "type" in data["database"]
    assert data["database"]["status"] in ["ok", "error"]


def test_health_endpoint_timestamp_format():
    """Test that the timestamp is in correct ISO format"""
    response = client.get("/health")
    data = response.json()

    # Parse timestamp to ensure it's valid ISO format
    timestamp = data["timestamp"]
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid timestamp format: {timestamp}")


@pytest.mark.asyncio
async def test_health_endpoint_async():
    """Test the health endpoint in async mode"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert data["database"]["status"] == "ok"


def test_health_endpoint_response_structure():
    """Test that the health endpoint response has the correct structure"""
    response = client.get("/health")
    data = response.json()

    # Check all required top-level fields
    required_fields = ["status", "timestamp", "version", "database", "environment"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check database object structure
    db_required_fields = ["status", "type"]
    for field in db_required_fields:
        assert field in data["database"], f"Missing database field: {field}"


def test_health_endpoint_consistent_responses():
    """Test that multiple calls to health endpoint return consistent structure"""
    responses = [client.get("/health") for _ in range(3)]

    # All should return 200
    for response in responses:
        assert response.status_code == 200

    # All should have the same structure
    data_list = [response.json() for response in responses]

    # Check that all responses have the same keys
    first_keys = set(data_list[0].keys())
    for data in data_list[1:]:
        assert set(data.keys()) == first_keys

    # Check that status and database status are consistent
    for data in data_list:
        assert data["status"] == "ok"
        assert data["database"]["status"] == "ok"
