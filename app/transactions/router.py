from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_session
from app.transactions.domain import TransactionType
from app.transactions.schemas import (
    CreateTransactionRequest,
    TransactionPageResponse,
    TransactionResponse,
)
from app.transactions.service import TransactionService

router = APIRouter(prefix="/accounts/{account_id}/transactions", tags=["transactions"])


def get_transaction_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TransactionService:
    return TransactionService(session)


TransactionServiceDependency = Annotated[TransactionService, Depends(get_transaction_service)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
async def add_transaction(
    account_id: UUID, request: CreateTransactionRequest, service: TransactionServiceDependency
):
    return await service.add_transaction(
        account_id, request.type, request.amount, request.description, request.reference_id
    )


@router.get("", response_model=TransactionPageResponse)
async def list_transactions(
    account_id: UUID,
    service: TransactionServiceDependency,
    type: TransactionType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = await service.list_transactions(account_id, type, page, limit)
    return TransactionPageResponse(
        items=[TransactionResponse.model_validate(item) for item in result.items],
        page=result.page,
        limit=result.limit,
        total=result.total,
        total_pages=result.total_pages,
    )
