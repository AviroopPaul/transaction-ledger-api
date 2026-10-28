from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain import Account
from app.accounts.repository import AccountRepository
from app.shared.pagination import Page
from app.transactions.domain import DuplicateTransaction, Transaction, TransactionType
from app.transactions.repository import TransactionRepository


class TransactionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.transactions = TransactionRepository(session)

    async def add_transaction(
        self,
        account_id: UUID,
        type: TransactionType,
        amount: Decimal,
        description: str | None,
        reference_id: str,
    ) -> Transaction:
        async with self.session.begin():
            account = await self.accounts.get(account_id, lock=True)
            return await self.post(account, type, amount, description, reference_id)

    async def post(
        self,
        account: Account,
        type: TransactionType,
        amount: Decimal,
        description: str | None,
        reference_id: str,
    ) -> Transaction:
        """Call this only inside an open database transaction, with the account row locked."""
        existing = await self.transactions.find_by_reference(account.id, reference_id)
        if existing:
            raise DuplicateTransaction(existing)

        transaction = Transaction.record(account.id, type, amount, description, reference_id)
        transaction.apply_to(account)
        await self.transactions.add(transaction)
        await self.accounts.save_balance(account)
        return transaction

    async def list_transactions(
        self, account_id: UUID, type: TransactionType | None, page: int, limit: int
    ) -> Page[Transaction]:
        await self.accounts.get(account_id)
        items, total = await self.transactions.list_for_account(account_id, type, page, limit)
        return Page(items=items, page=page, limit=limit, total=total)
