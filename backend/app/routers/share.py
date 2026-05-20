"""
Share router — public shareable report endpoints (PRD 5.5).
No login required. Enables one user to protect many others with one share.
"""
from fastapi import APIRouter, Request

from app.config import settings
from app.dependencies import DbDep
from app.schemas.analysis import AnalysisResponse
from app.schemas.common import APIResponse
from app.schemas.report import ShareableReportMeta
from app.services import analysis_service

router = APIRouter(prefix="/share", tags=["Shareable Reports"])


@router.get("/{slug}", response_model=APIResponse[AnalysisResponse])
async def get_shared_report(slug: str, db: DbDep):
    """
    Retrieve a public analysis report by its share slug.
    PRD 5.5: Anyone can view this without login — designed for group sharing.
    """
    analysis = await analysis_service.get_analysis_by_slug(slug, db)
    return APIResponse(data=AnalysisResponse.model_validate(analysis, from_attributes=True))


@router.get("/{slug}/meta", response_model=APIResponse[ShareableReportMeta])
async def get_share_meta(slug: str, request: Request, db: DbDep):
    """
    Get sharing metadata for an analysis — shareable URL + WhatsApp-ready text.
    PRD 5.5: 'Nada sopan dan tidak menghakimi — bisa dikirim ke grup WA.'
    """
    analysis = await analysis_service.get_analysis_by_slug(slug, db)

    # Build frontend share page URL (not the API endpoint)
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    share_url = f"{frontend_url}/share/{slug}"

    # Generate WhatsApp-friendly summary (PRD 5.5)
    risk_emoji = {
        "SAFE": "✅", "LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴", "CRITICAL": "🚨"
    }.get(analysis.riskLevel, "⚠️")

    ojk_text = ""
    if analysis.ojkStatus == "TERINDIKASI_ILEGAL":
        ojk_text = "\n❌ Status OJK: Terindikasi Ilegal oleh Satgas Waspada Investasi"
    elif analysis.ojkStatus == "TERDAFTAR":
        ojk_text = "\n✅ Status OJK: Terdaftar"

    wa_text = (
        f"Saya cek dulu pakai CekInvest, ini hasilnya:\n\n"
        f"{risk_emoji} Skor Risiko: {analysis.riskScore}/100 ({analysis.riskLevel})\n"
        f"{ojk_text}\n"
        f"📋 {analysis.summary or 'Lihat laporan lengkap untuk detail.'}\n\n"
        f"🔗 Laporan lengkap: {share_url}\n\n"
        f"_Dicek pakai CekInvest — AI Scam Intelligence gratis untuk semua_"
    )

    return APIResponse(
        data=ShareableReportMeta(
            shareUrl=share_url,
            shareSlug=slug,
            whatsappText=wa_text,
            analysisId=analysis.id,
        )
    )
