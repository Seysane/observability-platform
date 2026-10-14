import os
import sys

os.environ["FLASK_SKIP_AUTOCREATE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import psycopg
import pytest

from app import create_app

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL, reason="TEST_DATABASE_URL is not set (needs a PostgreSQL database)"
)


@pytest.fixture
def client():
    app = create_app(
        {"DATABASE_URL": TEST_DB_URL, "SEED_DEMO_DATA": False, "TESTING": True}
    )
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.execute("TRUNCATE orders RESTART IDENTITY")
    return app.test_client()


def add(client, customer="Test", item="Thing", amount="10"):
    return client.post(
        "/orders", data={"customer": customer, "item": item, "amount": amount}
    )


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_pages_render(client):
    for path in ("/", "/orders", "/about"):
        assert client.get(path).status_code == 200


def test_create_order_starts_open(client):
    assert add(client).status_code == 302
    assert b"Test" in client.get("/orders?status=open").data
    assert b"Test" not in client.get("/orders?status=fulfilled").data


def test_toggle_moves_order_between_views(client):
    add(client)
    client.post("/orders/1/toggle", data={"status": "all"})
    assert b"Test" in client.get("/orders?status=fulfilled").data
    assert b"Test" not in client.get("/orders?status=open").data
    client.post("/orders/1/toggle", data={"status": "all"})
    assert b"Test" in client.get("/orders?status=open").data


def test_decimal_amount_with_comma(client):
    add(client, amount="12,5")
    assert b"12.50 PLN" in client.get("/orders").data


def test_invalid_order_rejected(client):
    assert add(client, amount="abc").status_code == 400
    assert add(client, customer="").status_code == 400
    assert add(client, amount="-5").status_code == 400
    assert add(client, amount="1e20").status_code == 400


def test_unknown_status_and_order(client):
    assert client.get("/orders?status=nope").status_code == 404
    assert client.post("/orders/999/toggle").status_code == 404
