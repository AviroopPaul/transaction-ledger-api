from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain import Account
from app.accounts.repository import AccountRepository


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)

    async def open_account(self, name: str) -> Account:
        account = Account.open(name)
        async with self.session.begin():
            await self.accounts.add(account)
        return account

    async def get_account(self, account_id: UUID) -> Account:
        return await self.accounts.get(account_id)
