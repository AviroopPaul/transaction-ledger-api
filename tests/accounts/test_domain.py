from decimal import Decimal

import pytest

from app.accounts.domain import MAX_BALANCE, Account, BalanceLimitExceeded, InsufficientBalance


def test_open_account_starts_with_zero_balance():
    account = Account.open("Alice")

    assert account.name == "Alice"
    assert account.balance == Decimal("0")
    assert account.created_at is not None


def test_open_account_gives_unique_ids():
    assert Account.open("Alice").id != Account.open("Alice").id


def test_credit_increases_balance():
    account = Account.open("Alice")

    account.credit(Decimal("100"))
    account.credit(Decimal("50"))

    assert account.balance == Decimal("150")


def test_debit_decreases_balance():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    account.debit(Decimal("30"))

    assert account.balance == Decimal("70")


def test_debit_of_full_balance_is_allowed():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    account.debit(Decimal("100"))

    assert account.balance == Decimal("0")


def test_debit_above_balance_is_rejected_and_balance_stays_same():
    account = Account.open("Alice")
    account.credit(Decimal("100"))

    with pytest.raises(InsufficientBalance):
        account.debit(Decimal("150"))

    assert account.balance == Decimal("100")


def test_credit_above_maximum_balance_is_rejected_and_balance_stays_same():
    account = Account.open("Alice")
    account.credit(MAX_BALANCE)

    with pytest.raises(BalanceLimitExceeded):
        account.credit(Decimal("0.01"))

    assert account.balance == MAX_BALANCE
