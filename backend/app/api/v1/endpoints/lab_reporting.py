"""Read-only B9 science authority endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.lab_reporting import ScienceReportRepository
from app.schemas.lab_reporting import ScienceAuthorityReport, ScienceView
from app.services.lab_reporting import ScienceReportingService

router = APIRouter()


def _service(session: AsyncSession) -> ScienceReportingService:
    return ScienceReportingService(ScienceReportRepository(session))


@router.get("/authority", response_model=ScienceAuthorityReport)
async def science_authority(
    view: ScienceView = ScienceView.STRICT,
    session: AsyncSession = Depends(get_db),
) -> ScienceAuthorityReport:
    """Return the canonical non-promoting JSON authority report."""

    return await _service(session).authority_report(view)


@router.get("/report.md", response_class=PlainTextResponse)
async def science_authority_markdown(
    view: ScienceView = ScienceView.STRICT,
    session: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Render Markdown from the same canonical JSON projection."""

    content = await _service(session).markdown_report(view)
    return PlainTextResponse(content, media_type="text/markdown")


__all__ = ["router"]
