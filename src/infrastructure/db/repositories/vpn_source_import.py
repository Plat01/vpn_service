import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.vpn_catalog.entities import VpnSourceImport
from src.domain.vpn_catalog.repositories import VpnSourceImportRepository
from src.infrastructure.db.models import VpnSourceImportModel


class SqlAlchemyVpnSourceImportRepository(VpnSourceImportRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, import_: VpnSourceImport) -> VpnSourceImport:
        error_summary_json = (
            json.dumps(import_.error_summary) if import_.error_summary else None
        )
        model = VpnSourceImportModel(
            id=import_.id,
            import_group=import_.import_group,
            mode=import_.mode,
            dry_run=import_.dry_run,
            total_count=import_.total_count,
            valid_count=import_.valid_count,
            invalid_count=import_.invalid_count,
            created_count=import_.created_count,
            updated_count=import_.updated_count,
            deactivated_count=import_.deactivated_count,
            failed_count=import_.failed_count,
            created_at=import_.created_at,
            error_summary=error_summary_json,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, import_id: UUID) -> VpnSourceImport | None:
        stmt = select(VpnSourceImportModel).where(
            VpnSourceImportModel.id == import_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_recent(
        self, import_group: str | None = None, limit: int = 50
    ) -> list[VpnSourceImport]:
        stmt = select(VpnSourceImportModel).order_by(
            VpnSourceImportModel.created_at.desc()
        ).limit(limit)
        if import_group:
            stmt = stmt.where(VpnSourceImportModel.import_group == import_group)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    def _model_to_entity(self, model: VpnSourceImportModel) -> VpnSourceImport:
        error_summary = None
        if model.error_summary:
            try:
                error_summary = json.loads(model.error_summary)
            except json.JSONDecodeError:
                error_summary = None

        return VpnSourceImport(
            id=model.id,
            import_group=model.import_group,
            mode=model.mode,
            dry_run=model.dry_run,
            total_count=model.total_count,
            valid_count=model.valid_count,
            invalid_count=model.invalid_count,
            created_count=model.created_count,
            updated_count=model.updated_count,
            deactivated_count=model.deactivated_count,
            failed_count=model.failed_count,
            created_at=model.created_at,
            error_summary=error_summary,
        )