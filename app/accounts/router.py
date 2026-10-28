from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.schemas import AccountResponse, BalanceResponse, CreateAccountRequest
from app.accounts.service import AccountService
from app.shared.database import get_session

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_account_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AccountService:
    return AccountService(session)


AccountServiceDependency = Annotated[AccountService, Depends(get_account_service)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(request: CreateAccountRequest, service: AccountServiceDependency):
    return await service.open_account(request.name)


@router.get("/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(account_id: UUID, service: AccountServiceDependency):
    account = await service.get_account(account_id)
    return BalanceResponse(account_id=account.id, balance=account.balance)
