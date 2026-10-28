from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from app.shared.errors import BusinessRuleError, NotFoundError


class AccountNotFound(NotFoundError):
    code = "ACCOUNT_NOT_FOUND"

    def __init__(self, account_id: UUID):
        super().__init__(f"Account {account_id} does not exist.", {"account_id": str(account_id)})


class InsufficientBalance(BusinessRuleError):
    code = "INSUFFICIENT_BALANCE"

    def __init__(self, account_id: UUID, balance: Decimal, amount: Decimal):
        super().__init__(
            "The account balance is too low for this debit.",
            {"account_id": str(account_id), "balance": str(balance), "amount": str(amount)},
        )


@dataclass
class Account:
    id: UUID
    name: str
    balance: Decimal
    created_at: datetime

    @classmethod
    def open(cls, name: str) -> Account:
        return cls(id=uuid7(), name=name, balance=Decimal("0.00"), created_at=datetime.now(UTC))

    def credit(self, amount: Decimal) -> None:
        self.balance += amount

    def debit(self, amount: Decimal) -> None:
        if amount > self.balance:
            raise InsufficientBalance(self.id, self.balance, amount)
        self.balance -= amount
