from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_session
from app.transfers.schemas import CreateTransferRequest, TransferResponse
from app.transfers.service import TransferService

router = APIRouter(prefix="/transfers", tags=["transfers"])


def get_transfer_service(session: Annotated[AsyncSession, Depends(get_session)]) -> TransferService:
    return TransferService(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransferResponse)
async def create_transfer(
    request: CreateTransferRequest,
    service: Annotated[TransferService, Depends(get_transfer_service)],
):
    return await service.transfer(
        request.source_account_id,
        request.destination_account_id,
        request.amount,
        request.description,
        request.reference_id,
    )
