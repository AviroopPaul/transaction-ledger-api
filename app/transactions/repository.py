from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.transactions.domain import Transaction, TransactionType
from app.transactions.models import TransactionModel


def to_domain(row: TransactionModel) -> Transaction:
    return Transaction(
        id=row.id,
        account_id=row.account_id,
        type=TransactionType(row.type),
        amount=row.amount,
        description=row.description,
        reference_id=row.reference_id,
        created_at=row.created_at,
    )


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, transaction: Transaction) -> None:
        self.session.add(
            TransactionModel(
                id=transaction.id,
                account_id=transaction.account_id,
                type=transaction.type.value,
                amount=transaction.amount,
                description=transaction.description,
                reference_id=transaction.reference_id,
                created_at=transaction.created_at,
            )
        )

    async def find_by_reference(self, account_id: UUID, reference_id: str) -> Transaction | None:
        row = await self.session.scalar(
            select(TransactionModel).where(
                TransactionModel.account_id == account_id,
                TransactionModel.reference_id == reference_id,
            )
        )
        return to_domain(row) if row else None

    async def list_for_account(
        self, account_id: UUID, type: TransactionType | None, page: int, limit: int
    ) -> tuple[list[Transaction], int]:
        query = select(TransactionModel).where(TransactionModel.account_id == account_id)
        if type:
            query = query.where(TransactionModel.type == type.value)

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.session.scalars(
            query.order_by(TransactionModel.created_at.desc(), TransactionModel.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return [to_domain(row) for row in rows], total or 0
