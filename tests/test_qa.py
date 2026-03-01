from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_qa_endpoint():
    response = client.post("/api/qa", params={"question": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "Echo: Hello"
