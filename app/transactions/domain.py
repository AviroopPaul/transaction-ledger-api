from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from app.accounts.domain import Account
from app.shared.errors import ConflictError


class TransactionType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


@dataclass(frozen=True)
class Transaction:
    id: UUID
    account_id: UUID
    type: TransactionType
    amount: Decimal
    description: str | None
    reference_id: str
    created_at: datetime

    @classmethod
    def record(
        cls,
        account_id: UUID,
        type: TransactionType,
        amount: Decimal,
        description: str | None,
        reference_id: str,
    ) -> Transaction:
        return cls(
            id=uuid7(),
            account_id=account_id,
            type=type,
            amount=amount,
            description=description,
            reference_id=reference_id,
            created_at=datetime.now(UTC),
        )

    def apply_to(self, account: Account) -> None:
        if self.type is TransactionType.CREDIT:
            account.credit(self.amount)
        else:
            account.debit(self.amount)


class DuplicateTransaction(ConflictError):
    code = "DUPLICATE_TRANSACTION"

    def __init__(self, existing: Transaction):
        super().__init__(
            f"A transaction with reference_id '{existing.reference_id}' "
            "already exists for this account.",
            {
                "transaction_id": str(existing.id),
                "account_id": str(existing.account_id),
                "reference_id": existing.reference_id,
            },
        )
