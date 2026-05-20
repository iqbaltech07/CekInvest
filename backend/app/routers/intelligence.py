"""
Intelligence router v2.1 — SENTRA's scam pattern database and platform statistics.
Updated: community DB counts (phone reports, bank account reports, OJK cached entities).
All endpoints fully public.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.dependencies import DbDep
from app.schemas.common import APIResponse
from app.schemas.report import IntelligenceStatsResponse, ScamPatternResponse

router = APIRouter(prefix="/intelligence", tags=["Scam Intelligence"])


@router.get("/patterns", response_model=APIResponse[list[ScamPatternResponse]])
async def list_patterns(
    db: DbDep,
    category: str | None = Query(None, description="Filter by scam category"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List known scam patterns from SENTRA's intelligence database."""
    where = {"category": category} if category else {}
    patterns = await db.scampattern.find_many(
        where=where,
        order={"reportCount": "desc"},
        skip=(page - 1) * per_page,
        take=per_page,
    )
    return APIResponse(
        data=[ScamPatternResponse.model_validate(p, from_attributes=True) for p in patterns]
    )


@router.get("/stats", response_model=APIResponse[IntelligenceStatsResponse])
async def get_stats(db: DbDep):
    """
    Get platform-wide scam intelligence statistics.
    v2.1: includes community DB counts and OJK cached entities.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    (
        total_analyses, total_reports, total_patterns, high_risk_today,
        ojk_cached, phone_reports, bank_reports,
    ) = await _gather_stats(db, today_start)

    top_pattern = await db.scampattern.find_first(order={"reportCount": "desc"})

    return APIResponse(
        data=IntelligenceStatsResponse(
            totalAnalyses=total_analyses,
            totalReports=total_reports,
            totalScamPatterns=total_patterns,
            highRiskAnalysesToday=high_risk_today,
            mostCommonScamCategory=top_pattern.category if top_pattern else None,
            totalOjkCachedEntities=ojk_cached,
            totalCommunityPhoneReports=phone_reports,
            totalCommunityBankReports=bank_reports,
        )
    )


@router.get("/ojk-cache", response_model=APIResponse[list[dict]])
async def list_ojk_cache(
    db: DbDep,
    status: str | None = Query(None, description="Filter by status: LEGAL, ILLEGAL, WARNING"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List cached OJK entity checks. Useful for debugging and transparency."""
    where = {"status": status} if status else {}
    entities = await db.ojkentitycache.find_many(
        where=where,
        order={"cachedAt": "desc"},
        skip=(page - 1) * per_page,
        take=per_page,
    )
    return APIResponse(data=[
        {
            "entityName": e.entityName,
            "status": e.status,
            "detail": e.detail,
            "cachedAt": e.cachedAt.isoformat(),
        }
        for e in entities
    ])


async def _gather_stats(db, today_start: datetime) -> tuple[int, int, int, int, int, int, int]:
    """Run all count queries via Prisma."""
    from prisma.enums import RiskLevel

    total_analyses = await db.analysis.count()
    total_reports = await db.userreport.count()
    total_patterns = await db.scampattern.count()
    high_risk_today = await db.analysis.count(
        where={
            "riskLevel": {"in": [RiskLevel.HIGH, RiskLevel.CRITICAL]},
            "createdAt": {"gte": today_start},
        }
    )
    ojk_cached = await db.ojkentitycache.count()
    phone_reports = await db.phonereport.count()
    bank_reports = await db.bankaccountreport.count()

    return total_analyses, total_reports, total_patterns, high_risk_today, ojk_cached, phone_reports, bank_reports
