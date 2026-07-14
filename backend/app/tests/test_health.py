def test_health_endpoint(client):
    """Test that the health endpoint returns expected payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "online (test mode)"
    assert data["version"] == "1.0.0"
    assert "ai_engine" in data
