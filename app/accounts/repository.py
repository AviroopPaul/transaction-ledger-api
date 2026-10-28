from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain import Account, AccountNotFound
from app.accounts.models import AccountModel


class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, account: Account) -> None:
        self.session.add(
            AccountModel(
                id=account.id,
                name=account.name,
                balance=account.balance,
                created_at=account.created_at,
            )
        )

    async def get(self, account_id: UUID, lock: bool = False) -> Account:
        query = select(AccountModel).where(AccountModel.id == account_id)
        if lock:
            query = query.with_for_update()
        row = await self.session.scalar(query)
        if row is None:
            raise AccountNotFound(account_id)
        return Account(id=row.id, name=row.name, balance=row.balance, created_at=row.created_at)

    async def save_balance(self, account: Account) -> None:
        await self.session.execute(
            update(AccountModel)
            .where(AccountModel.id == account.id)
            .values(balance=account.balance)
        )
