"""
Clustering & Regional Monitoring Router.

Endpoints:
  GET  /api/v1/clustering/clusters   — list all scam clusters (filterable)
  GET  /api/v1/clustering/regional   — regional monitoring dashboard
  POST /api/v1/clustering/analyze    — manually feed one report into the clustering engine
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from app.dependencies import DbDep
from app.services.clustering_service import run_clustering

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clustering", tags=["Clustering"])


# ── GET /clusters ─────────────────────────────────────────────────────────────

@router.get("/clusters", summary="List scam clusters")
async def list_clusters(
    db: DbDep,
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW | MEDIUM | HIGH | CRITICAL"),
    region: Optional[str] = Query(None, description="Filter by dominant region (city name)"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Return all scam clusters detected by the rule-based engine.
    Supports filtering by risk level and region.
    """
    where: dict = {}
    if risk_level:
        where["riskLevel"] = risk_level.upper()
    if region:
        where["dominantRegion"] = {"contains": region, "mode": "insensitive"}

    # Only show scam clusters that have reached the threshold of at least 3 reports
    where["totalReports"] = {"gte": 3}

    clusters = await db.scamcluster.find_many(
        where=where,
        order={"totalReports": "desc"},
        take=limit,
    )

    return {
        "success": True,
        "data": {
            "total": len(clusters),
            "clusters": [
                {
                    "id": c.id,
                    "group_name": c.groupName,
                    "category": c.category,
                    "risk_level": c.riskLevel.value if hasattr(c.riskLevel, "value") else c.riskLevel,
                    "total_reports": c.totalReports,
                    "similarity_score": round(c.similarityScore * 100, 1),
                    "matched_signals": c.matchedSignals,
                    "dominant_region": c.dominantRegion,
                    "regional_status": c.regionalStatus.value if hasattr(c.regionalStatus, "value") else c.regionalStatus,
                    "bank_accounts": c.bankAccounts,
                    "phone_numbers": c.phoneNumbers,
                    "domains": c.domains,
                    "created_at": c.createdAt.isoformat() if c.createdAt else None,
                    "updated_at": c.updatedAt.isoformat() if c.updatedAt else None,
                }
                for c in clusters
            ],
        },
    }


# ── GET /regional ─────────────────────────────────────────────────────────────

@router.get("/regional", summary="Regional monitoring dashboard")
async def regional_dashboard(
    db: DbDep,
    trend: Optional[str] = Query(None, description="Filter by trend: STABLE | RISING | SPIKING | VIRAL"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Return regional monitoring stats sorted by growth percentage.
    Use trend filter to find VIRAL or SPIKING regions.
    """
    where: dict = {}
    if trend:
        where["trend"] = trend.upper()

    # Thresholding: Only monitor regions that have accumulated at least 3 reports
    where["totalReports"] = {"gte": 3}

    regions = await db.regionalmonitoring.find_many(
        where=where,
        order={"growthPercentage": "desc"},
        take=limit,
    )

    most_viral = [
        r for r in regions 
        if (r.trend.value if hasattr(r.trend, "value") else str(r.trend)) in ("VIRAL", "SPIKING")
    ]

    return {
        "success": True,
        "data": {
            "total_monitored_regions": len(regions),
            "most_viral_regions": [
                {
                    "region": r.region,
                    "province": r.province,
                    "dominant_scam": r.dominantScamCategory,
                    "growth_percentage": r.growthPercentage,
                    "status": r.trend.value if hasattr(r.trend, "value") else r.trend,
                    "spread_level": r.spreadLevel.value if hasattr(r.spreadLevel, "value") else r.spreadLevel,
                    "total_reports": r.totalReports,
                    "current_week": r.currentWeekReports,
                    "previous_week": r.previousWeekReports,
                    "updated_at": r.updatedAt.isoformat() if r.updatedAt else None,
                }
                for r in most_viral
            ],
            "all_regions": [
                {
                    "region": r.region,
                    "province": r.province,
                    "dominant_scam": r.dominantScamCategory,
                    "growth_percentage": r.growthPercentage,
                    "status": r.trend.value if hasattr(r.trend, "value") else r.trend,
                    "spread_level": r.spreadLevel.value if hasattr(r.spreadLevel, "value") else r.spreadLevel,
                    "total_reports": r.totalReports,
                }
                for r in regions
            ],
        },
    }


# ── POST /analyze ─────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class ClusteringAnalyzeRequest(BaseModel):
    report_text: str = Field(..., min_length=10, description="Scam report text to cluster")
    report_id: str = Field(..., description="ID of the persisted UserReport record")
    category: str = Field("Investasi Mencurigakan", description="Scam category label")
    city: Optional[str] = Field(None, description="City where the report originated")
    province: Optional[str] = Field(None, description="Province")
    domain: Optional[str] = Field(None, description="Suspicious domain (if any)")
    phone: Optional[str] = Field(None, description="Suspicious phone number (if any)")
    bank_account: Optional[str] = Field(None, description="Suspicious bank account (if any)")
    domain_age_days: Optional[int] = Field(None, description="Domain age in days (from WHOIS)")


@router.post("/analyze", summary="Feed a report into the clustering engine")
async def clustering_analyze(
    body: ClusteringAnalyzeRequest,
    db: DbDep,
):
    """
    Manually submit one report to the clustering engine.
    Useful for integration testing or re-clustering an existing report.
    Zero AI calls — pure rule-based processing.
    """
    result = await run_clustering(
        db,
        report_id=body.report_id,
        report_text=body.report_text,
        category=body.category,
        domain=body.domain,
        phone=body.phone,
        bank_account=body.bank_account,
        domain_age_days=body.domain_age_days,
        city=body.city,
        province=body.province,
    )
    return {
        "success": True,
        "data": result,
    }
