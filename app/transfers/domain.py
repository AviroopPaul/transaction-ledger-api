from dataclasses import dataclass
from uuid import UUID

from app.shared.errors import BusinessRuleError
from app.transactions.domain import Transaction


class SameAccountTransfer(BusinessRuleError):
    code = "SAME_ACCOUNT_TRANSFER"

    def __init__(self, account_id: UUID):
        super().__init__(
            "The source and destination accounts must be different.",
            {"account_id": str(account_id)},
        )


@dataclass(frozen=True)
class Transfer:
    debit: Transaction
    credit: Transaction
