import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_account(client: AsyncClient, name: str = "Alice") -> str:
    response = await client.post("/api/v1/accounts", json={"name": name})
    return response.json()["id"]


async def add_transaction(
    client: AsyncClient, account_id: str, type: str, amount, reference_id: str, **extra
):
    return await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={"type": type, "amount": amount, "reference_id": reference_id, **extra},
    )


async def get_balance(client: AsyncClient, account_id: str) -> str:
    response = await client.get(f"/api/v1/accounts/{account_id}/balance")
    return response.json()["balance"]


async def test_credit_creates_transaction_and_increases_balance(client: AsyncClient):
    account_id = await create_account(client)

    response = await add_transaction(
        client, account_id, "credit", 100, "ref-1", description="Salary"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["account_id"] == account_id
    assert body["type"] == "credit"
    assert body["amount"] == "100.00"
    assert body["description"] == "Salary"
    assert body["reference_id"] == "ref-1"
    assert body["id"]
    assert body["created_at"]
    assert await get_balance(client, account_id) == "100.00"


async def test_debit_decreases_balance(client: AsyncClient):
    account_id = await create_account(client)
    await add_transaction(client, account_id, "credit", 100, "ref-1")

    response = await add_transaction(client, account_id, "debit", 30, "ref-2")

    assert response.status_code == 201
    assert await get_balance(client, account_id) == "70.00"


async def test_debit_above_balance_is_rejected_and_balance_stays_same(client: AsyncClient):
    account_id = await create_account(client)
    await add_transaction(client, account_id, "credit", 100, "ref-1")

    response = await add_transaction(client, account_id, "debit", 150, "ref-2")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert await get_balance(client, account_id) == "100.00"
    history = await client.get(f"/api/v1/accounts/{account_id}/transactions")
    assert history.json()["total"] == 1


async def test_rejected_debit_reference_can_be_used_again(client: AsyncClient):
    account_id = await create_account(client)
    await add_transaction(client, account_id, "debit", 50, "ref-1")
    await add_transaction(client, account_id, "credit", 100, "ref-2")

    response = await add_transaction(client, account_id, "debit", 50, "ref-1")

    assert response.status_code == 201
    assert await get_balance(client, account_id) == "50.00"


async def test_duplicate_reference_is_rejected_and_balance_stays_same(client: AsyncClient):
    account_id = await create_account(client)
    first = await add_transaction(client, account_id, "credit", 100, "ref-1")

    response = await add_transaction(client, account_id, "credit", 100, "ref-1")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DUPLICATE_TRANSACTION"
    assert error["details"]["transaction_id"] == first.json()["id"]
    assert await get_balance(client, account_id) == "100.00"
    history = await client.get(f"/api/v1/accounts/{account_id}/transactions")
    assert history.json()["total"] == 1


async def test_same_reference_is_allowed_on_different_accounts(client: AsyncClient):
    alice = await create_account(client, "Alice")
    bob = await create_account(client, "Bob")

    first = await add_transaction(client, alice, "credit", 10, "ref-1")
    second = await add_transaction(client, bob, "credit", 20, "ref-1")

    assert first.status_code == 201
    assert second.status_code == 201


async def test_balance_is_result_of_all_valid_transactions(client: AsyncClient):
    account_id = await create_account(client)
    entries = [("credit", 100), ("credit", 50), ("debit", 30), ("debit", 20)]

    for index, (type, amount) in enumerate(entries):
        await add_transaction(client, account_id, type, amount, f"ref-{index}")

    assert await get_balance(client, account_id) == "100.00"


async def test_transaction_on_unknown_account_returns_404(client: AsyncClient):
    response = await add_transaction(client, str(uuid4()), "credit", 10, "ref-1")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"type": "refund", "amount": 10, "reference_id": "r"}, "body.type"),
        ({"type": "credit", "amount": 0, "reference_id": "r"}, "body.amount"),
        ({"type": "credit", "amount": -5, "reference_id": "r"}, "body.amount"),
        ({"type": "credit", "amount": 10.555, "reference_id": "r"}, "body.amount"),
        ({"type": "credit", "amount": "abc", "reference_id": "r"}, "body.amount"),
        ({"type": "credit", "amount": 10}, "body.reference_id"),
        ({"type": "credit", "amount": 10, "reference_id": "  "}, "body.reference_id"),
        ({"amount": 10, "reference_id": "r"}, "body.type"),
        ({"type": "credit", "amount": 10, "reference_id": "r", "id": "x"}, "body.id"),
    ],
)
async def test_invalid_transaction_data_returns_422(client: AsyncClient, payload, field):
    account_id = await create_account(client)

    response = await client.post(f"/api/v1/accounts/{account_id}/transactions", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in [item["field"] for item in error["details"]["fields"]]
    assert await get_balance(client, account_id) == "0.00"


async def test_history_is_latest_first(client: AsyncClient):
    account_id = await create_account(client)
    for index in range(3):
        await add_transaction(client, account_id, "credit", 10, f"ref-{index}")

    response = await client.get(f"/api/v1/accounts/{account_id}/transactions")

    references = [item["reference_id"] for item in response.json()["items"]]
    assert references == ["ref-2", "ref-1", "ref-0"]


async def test_history_filters_by_type(client: AsyncClient):
    account_id = await create_account(client)
    await add_transaction(client, account_id, "credit", 100, "ref-1")
    await add_transaction(client, account_id, "debit", 10, "ref-2")
    await add_transaction(client, account_id, "credit", 5, "ref-3")
    url = f"/api/v1/accounts/{account_id}/transactions"

    credits = (await client.get(url, params={"type": "credit"})).json()
    debits = (await client.get(url, params={"type": "debit"})).json()
    everything = (await client.get(url)).json()

    assert {item["type"] for item in credits["items"]} == {"credit"}
    assert credits["total"] == 2
    assert {item["type"] for item in debits["items"]} == {"debit"}
    assert debits["total"] == 1
    assert everything["total"] == 3


async def test_history_paginates(client: AsyncClient):
    account_id = await create_account(client)
    for index in range(5):
        await add_transaction(client, account_id, "credit", 10, f"ref-{index}")
    url = f"/api/v1/accounts/{account_id}/transactions"

    second_page = (await client.get(url, params={"page": 2, "limit": 2})).json()
    last_page = (await client.get(url, params={"page": 3, "limit": 2})).json()
    past_end = (await client.get(url, params={"page": 4, "limit": 2})).json()

    assert [item["reference_id"] for item in second_page["items"]] == ["ref-2", "ref-1"]
    assert second_page["page"] == 2
    assert second_page["limit"] == 2
    assert second_page["total"] == 5
    assert second_page["total_pages"] == 3
    assert [item["reference_id"] for item in last_page["items"]] == ["ref-0"]
    assert past_end["items"] == []


async def test_history_of_account_without_transactions_is_empty(client: AsyncClient):
    account_id = await create_account(client)

    response = await client.get(f"/api/v1/accounts/{account_id}/transactions")

    assert response.json() == {"items": [], "page": 1, "limit": 20, "total": 0, "total_pages": 0}


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page": -1}, {"limit": 0}, {"limit": 101}, {"page": "x"}, {"type": "refund"}],
)
async def test_history_with_invalid_query_returns_422(client: AsyncClient, params):
    account_id = await create_account(client)

    response = await client.get(f"/api/v1/accounts/{account_id}/transactions", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_history_of_unknown_account_returns_404(client: AsyncClient):
    response = await client.get(f"/api/v1/accounts/{uuid4()}/transactions")

    assert response.status_code == 404


async def test_transactions_cannot_be_edited_or_deleted(client: AsyncClient):
    account_id = await create_account(client)
    created = await add_transaction(client, account_id, "credit", 10, "ref-1")
    collection_url = f"/api/v1/accounts/{account_id}/transactions"
    item_url = f"{collection_url}/{created.json()['id']}"

    for method in ("PUT", "PATCH", "DELETE"):
        assert (await client.request(method, collection_url)).status_code == 405
        assert (await client.request(method, item_url)).status_code == 404

    history = (await client.get(collection_url)).json()
    assert history["items"][0] == created.json()


async def test_parallel_debits_never_overdraw_account(client: AsyncClient):
    account_id = await create_account(client)
    await add_transaction(client, account_id, "credit", 100, "seed")

    responses = await asyncio.gather(
        *[add_transaction(client, account_id, "debit", 20, f"ref-{index}") for index in range(10)]
    )

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [201] * 5 + [422] * 5
    assert await get_balance(client, account_id) == "0.00"


async def test_parallel_duplicates_create_one_transaction(client: AsyncClient):
    account_id = await create_account(client)

    responses = await asyncio.gather(
        *[add_transaction(client, account_id, "credit", 10, "same-ref") for _ in range(5)]
    )

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [201] + [409] * 4
    assert await get_balance(client, account_id) == "10.00"
