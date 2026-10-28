from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.repository import AccountRepository
from app.transactions.domain import TransactionType
from app.transactions.service import TransactionService
from app.transfers.domain import SameAccountTransfer, Transfer


class TransferService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.transactions = TransactionService(session)

    async def transfer(
        self,
        source_id: UUID,
        destination_id: UUID,
        amount: Decimal,
        description: str | None,
        reference_id: str,
    ) -> Transfer:
        if source_id == destination_id:
            raise SameAccountTransfer(source_id)

        async with self.session.begin():
            # Lock the rows in a fixed order to prevent deadlocks between opposite transfers.
            accounts = {
                account_id: await self.accounts.get(account_id, lock=True)
                for account_id in sorted([source_id, destination_id])
            }
            debit = await self.transactions.post(
                accounts[source_id], TransactionType.DEBIT, amount, description, reference_id
            )
            credit = await self.transactions.post(
                accounts[destination_id], TransactionType.CREDIT, amount, description, reference_id
            )
        return Transfer(debit=debit, credit=credit)
