from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError
from main import app

def test_cors_headers(client):
    """Test that CORS middleware is attached (implicitly verified by successful requests or preflights)."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    # If CORS is setup, it should return 200 OK for OPTIONS
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

def test_exception_handler_value_error(client):
    """Test global ValueError handler."""
    # Temporarily add a route that raises ValueError
    @app.get("/api/v1/test_value_error")
    def trigger_value_error():
        raise ValueError("Invalid input provided")
        
    response = client.get("/api/v1/test_value_error")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid input provided"

def test_exception_handler_sqlalchemy_error(client):
    """Test global SQLAlchemyError handler."""
    @app.get("/api/v1/test_db_error")
    def trigger_db_error():
        raise SQLAlchemyError("Connection failed")
        
    response = client.get("/api/v1/test_db_error")
    assert response.status_code == 500
    assert "database operation" in response.json()["detail"]
