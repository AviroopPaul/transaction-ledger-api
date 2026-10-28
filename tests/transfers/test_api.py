import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_account(client: AsyncClient, name: str, opening_credit: int = 0) -> str:
    account_id = (await client.post("/api/v1/accounts", json={"name": name})).json()["id"]
    if opening_credit:
        await client.post(
            f"/api/v1/accounts/{account_id}/transactions",
            json={"type": "credit", "amount": opening_credit, "reference_id": "opening"},
        )
    return account_id


async def transfer(client: AsyncClient, source: str, destination: str, amount, reference_id: str):
    return await client.post(
        "/api/v1/transfers",
        json={
            "source_account_id": source,
            "destination_account_id": destination,
            "amount": amount,
            "reference_id": reference_id,
        },
    )


async def get_balance(client: AsyncClient, account_id: str) -> str:
    response = await client.get(f"/api/v1/accounts/{account_id}/balance")
    return response.json()["balance"]


async def count_transactions(client: AsyncClient, account_id: str) -> int:
    response = await client.get(f"/api/v1/accounts/{account_id}/transactions")
    return response.json()["total"]


async def test_transfer_moves_money_between_accounts(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)
    bob = await create_account(client, "Bob", 50)

    response = await transfer(client, alice, bob, 30, "transfer-1")

    assert response.status_code == 201
    body = response.json()
    assert body["debit"]["account_id"] == alice
    assert body["debit"]["type"] == "debit"
    assert body["debit"]["amount"] == "30.00"
    assert body["credit"]["account_id"] == bob
    assert body["credit"]["type"] == "credit"
    assert body["credit"]["reference_id"] == "transfer-1"
    assert await get_balance(client, alice) == "70.00"
    assert await get_balance(client, bob) == "80.00"


async def test_transfer_with_insufficient_balance_changes_nothing(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)
    bob = await create_account(client, "Bob", 50)

    response = await transfer(client, alice, bob, 150, "transfer-1")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert await get_balance(client, alice) == "100.00"
    assert await get_balance(client, bob) == "50.00"
    assert await count_transactions(client, alice) == 1
    assert await count_transactions(client, bob) == 1


@pytest.mark.parametrize("missing_side", ["source", "destination"])
async def test_transfer_with_unknown_account_returns_404(client: AsyncClient, missing_side):
    alice = await create_account(client, "Alice", 100)
    unknown = str(uuid4())
    source, destination = (unknown, alice) if missing_side == "source" else (alice, unknown)

    response = await transfer(client, source, destination, 30, "transfer-1")

    assert response.status_code == 404
    assert response.json()["error"]["details"]["account_id"] == unknown
    assert await get_balance(client, alice) == "100.00"


async def test_transfer_to_same_account_is_rejected(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)

    response = await transfer(client, alice, alice, 30, "transfer-1")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SAME_ACCOUNT_TRANSFER"
    assert await get_balance(client, alice) == "100.00"


async def test_duplicate_transfer_is_rejected(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)
    bob = await create_account(client, "Bob")
    await transfer(client, alice, bob, 30, "transfer-1")

    response = await transfer(client, alice, bob, 30, "transfer-1")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_TRANSACTION"
    assert await get_balance(client, alice) == "70.00"
    assert await get_balance(client, bob) == "30.00"


async def test_failed_credit_rolls_back_debit(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)
    bob = await create_account(client, "Bob")
    await client.post(
        f"/api/v1/accounts/{bob}/transactions",
        json={"type": "credit", "amount": 5, "reference_id": "transfer-1"},
    )

    response = await transfer(client, alice, bob, 30, "transfer-1")

    assert response.status_code == 409
    assert response.json()["error"]["details"]["account_id"] == bob
    assert await get_balance(client, alice) == "100.00"
    assert await count_transactions(client, alice) == 1
    assert await get_balance(client, bob) == "5.00"


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": -10},
        {"reference_id": ""},
        {"source_account_id": "not-a-uuid"},
        {"destination_account_id": None},
        {"unknown_field": "x"},
    ],
)
async def test_invalid_transfer_data_returns_422(client: AsyncClient, overrides):
    payload = {
        "source_account_id": str(uuid4()),
        "destination_account_id": str(uuid4()),
        "amount": 10,
        "reference_id": "transfer-1",
        **overrides,
    }

    response = await client.post("/api/v1/transfers", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_parallel_opposite_transfers_keep_total_and_do_not_deadlock(client: AsyncClient):
    alice = await create_account(client, "Alice", 100)
    bob = await create_account(client, "Bob", 100)

    responses = await asyncio.gather(
        *[
            transfer(client, alice, bob, 10, f"a-to-b-{index}")
            if index % 2 == 0
            else transfer(client, bob, alice, 10, f"b-to-a-{index}")
            for index in range(20)
        ]
    )

    assert all(response.status_code == 201 for response in responses)
    assert await get_balance(client, alice) == "100.00"
    assert await get_balance(client, bob) == "100.00"
