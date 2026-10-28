from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid7

import pytest

from app.accounts.domain import Account, InsufficientBalance
from app.transactions.domain import Transaction, TransactionType


def record(account: Account, type: TransactionType, amount: str, reference_id: str = "ref-1"):
    return Transaction.record(account.id, type, Decimal(amount), None, reference_id)


def test_record_sets_system_fields():
    account_id = uuid7()

    transaction = Transaction.record(
        account_id, TransactionType.CREDIT, Decimal("50"), "Salary", "ref-1"
    )

    assert transaction.account_id == account_id
    assert transaction.type is TransactionType.CREDIT
    assert transaction.amount == Decimal("50")
    assert transaction.description == "Salary"
    assert transaction.reference_id == "ref-1"
    assert transaction.id is not None
    assert transaction.created_at is not None


def test_transaction_cannot_be_changed():
    transaction = record(Account.open("Alice"), TransactionType.CREDIT, "50")

    with pytest.raises(FrozenInstanceError):
        transaction.amount = Decimal("500")  # type: ignore[misc]


def test_credit_increases_account_balance():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    record(account, TransactionType.CREDIT, "50").apply_to(account)

    assert account.balance == Decimal("150")


def test_debit_decreases_account_balance():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    record(account, TransactionType.DEBIT, "30").apply_to(account)

    assert account.balance == Decimal("70")


def test_debit_above_balance_is_rejected():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    with pytest.raises(InsufficientBalance):
        record(account, TransactionType.DEBIT, "150").apply_to(account)

    assert account.balance == Decimal("100")


def test_balance_is_result_of_all_valid_transactions():
    account = Account.open("Alice")
    entries = [("credit", "100"), ("credit", "50"), ("debit", "30"), ("debit", "20")]

    for type, amount in entries:
        record(account, TransactionType(type), amount).apply_to(account)

    assert account.balance == Decimal("100")
