from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.transactions.domain import TransactionType

Amount = Annotated[
    Decimal,
    Field(gt=0, max_digits=18, decimal_places=2),
    AfterValidator(lambda amount: amount.quantize(Decimal("0.01"))),
]
ReferenceId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class CreateTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TransactionType
    amount: Amount
    description: Description | None = None
    reference_id: ReferenceId


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    type: TransactionType
    amount: Decimal
    description: str | None
    reference_id: str
    created_at: datetime


class TransactionPageResponse(BaseModel):
    items: list[TransactionResponse]
    page: int
    limit: int
    total: int
    total_pages: int
