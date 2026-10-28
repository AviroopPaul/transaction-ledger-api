from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.transactions.schemas import Amount, Description, ReferenceId, TransactionResponse


class CreateTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_account_id: UUID
    destination_account_id: UUID
    amount: Amount
    description: Description | None = None
    reference_id: ReferenceId


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    debit: TransactionResponse
    credit: TransactionResponse
