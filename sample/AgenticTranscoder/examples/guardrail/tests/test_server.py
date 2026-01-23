"""Server tests."""

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
