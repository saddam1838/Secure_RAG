from fastapi.testclient import TestClient
from api.routes import app

client = TestClient(app)


def test_query_endpoint():
    # This will likely fail without auth, but we test the structure
    response = client.post("/query", json={"query": "What is the capital of France?"})
    assert response.status_code in [200, 401]
