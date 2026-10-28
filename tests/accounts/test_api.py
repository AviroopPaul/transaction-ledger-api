from uuid import uuid4

from httpx import AsyncClient


async def test_create_account_returns_new_account_with_zero_balance(client: AsyncClient):
    response = await client.post("/api/v1/accounts", json={"name": "Alice"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["balance"] == "0.00"
    assert body["id"]
    assert body["created_at"]


async def test_create_account_trims_name(client: AsyncClient):
    response = await client.post("/api/v1/accounts", json={"name": "  Alice  "})

    assert response.json()["name"] == "Alice"


async def test_create_account_gives_unique_ids(client: AsyncClient):
    first = await client.post("/api/v1/accounts", json={"name": "Alice"})
    second = await client.post("/api/v1/accounts", json={"name": "Alice"})

    assert first.json()["id"] != second.json()["id"]


async def test_create_account_rejects_client_balance(client: AsyncClient):
    response = await client.post("/api/v1/accounts", json={"name": "Alice", "balance": 500})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_account_rejects_client_id_and_created_at(client: AsyncClient):
    response = await client.post(
        "/api/v1/accounts",
        json={"name": "Alice", "id": str(uuid4()), "created_at": "2020-01-01T00:00:00Z"},
    )

    assert response.status_code == 422


async def test_create_account_requires_name(client: AsyncClient):
    response = await client.post("/api/v1/accounts", json={})

    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    assert fields[0]["field"] == "body.name"


async def test_create_account_rejects_blank_name(client: AsyncClient):
    response = await client.post("/api/v1/accounts", json={"name": "   "})

    assert response.status_code == 422


async def test_create_account_rejects_invalid_json(client: AsyncClient):
    response = await client.post(
        "/api/v1/accounts", content="not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_get_balance_returns_account_balance(client: AsyncClient):
    account = (await client.post("/api/v1/accounts", json={"name": "Alice"})).json()

    response = await client.get(f"/api/v1/accounts/{account['id']}/balance")

    assert response.status_code == 200
    assert response.json() == {"account_id": account["id"], "balance": "0.00"}


async def test_get_balance_of_unknown_account_returns_404(client: AsyncClient):
    account_id = str(uuid4())

    response = await client.get(f"/api/v1/accounts/{account_id}/balance")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "ACCOUNT_NOT_FOUND",
            "message": f"Account {account_id} does not exist.",
            "details": {"account_id": account_id},
        }
    }


async def test_get_balance_with_malformed_id_returns_422(client: AsyncClient):
    response = await client.get("/api/v1/accounts/not-a-uuid/balance")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
