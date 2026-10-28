
import pytest
import tempfile
import os
import app as expense_app


@pytest.fixture
def client():
    # Create a separate temporary database for this test.
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    original_db_path = expense_app.DB_PATH
    expense_app.DB_PATH = db_path
    expense_app.init_db()

    expense_app.app.config["TESTING"] = True

    with expense_app.app.test_client() as test_client:
        yield test_client

    expense_app.DB_PATH = original_db_path

    # Close any connections before removing the database.
    try:
        os.remove(db_path)
    except PermissionError:
        pass


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Expense Dashboard" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_add_expense(client):
    response = client.post("/api/expenses", json={
        "title": "Office Supplies",
        "category": "Equipment",
        "amount": 2500,
        "expense_date": "2026-10-26",
        "description": "Stationery"
    })

    assert response.status_code == 201

    result = client.get(
        "/api/expenses?month=2026-10"
    ).get_json()

    assert result["count"] == 1
    assert result["total"] == 2500


def test_reject_invalid_expense(client):
    response = client.post("/api/expenses", json={
        "title": "Invalid Expense",
        "category": "Equipment",
        "amount": -100,
        "expense_date": "2026-10-26"
    })

    assert response.status_code == 400

def test_financial_assistant(client):
    response = client.post("/api/assistant", json={
        "question": "Give me a summary"
    })

    assert response.status_code == 200
    result = response.get_json()
    assert "answer" in result
    assert len(result["answer"]) > 0


def test_financial_insights(client):
    response = client.get("/api/insights?month=2026-10")

    assert response.status_code == 200
    result = response.get_json()

    assert result["month"] == "2026-10"
    assert "total" in result
    assert "budget" in result
    assert "remaining" in result
    assert "insights" in result

