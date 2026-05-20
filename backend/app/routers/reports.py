"""
Reports router — anonymous community scam report submission and listing.
No login required. Powers the Intelligence Flywheel from the PRD.
"""
import logging

from fastapi import APIRouter, Query, HTTPException

from app.dependencies import DbDep
from app.schemas.common import APIResponse
from app.schemas.report import CreateReportRequest, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Community Reports"])


import re

def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return None
    # Normalize Indonesia prefix: 628... or 8... to 08...
    if digits.startswith("62"):
        digits = "0" + digits[2:]
    elif digits.startswith("8"):
        digits = "0" + digits
    return digits

def normalize_bank_account(account: str | None) -> str | None:
    if not account:
        return None
    # Retain only digits for bank accounts (removes spaces, hyphens, etc.)
    return re.sub(r'\D', '', account)

WHITELISTED_DOMAINS = {
    # Government & Regulatory
    "go.id", "mil.id", "ojk.go.id", "bi.go.id", "kominfo.go.id", "indonesia.go.id", "pajak.go.id",
    # Banking
    "bca.co.id", "klikbca.com", "bankmandiri.co.id", "mandirikartukredit.com", "bni.co.id", "bri.co.id", "cimbniaga.co.id", "btn.co.id", "danamon.co.id",
    # Tech & E-commerce Giants
    "tokopedia.com", "shopee.co.id", "shopee.com", "bukalapak.com", "blibli.com", "gojek.com", "grab.com", "traveloka.com", "lazada.co.id",
    # Global Tech
    "google.com", "microsoft.com", "apple.com", "facebook.com", "instagram.com", "whatsapp.com", "youtube.com", "twitter.com", "x.com"
}

import urllib.request
import json
from datetime import datetime, timezone

def is_whitelisted_domain(domain: str | None) -> bool:
    if not domain:
        return False
    d = domain.lower().strip()
    if d.startswith("www."):
        d = d[4:]
    for whitelisted in WHITELISTED_DOMAINS:
        if d == whitelisted or d.endswith("." + whitelisted):
            return True
    return False

def get_domain_age_days(domain: str | None) -> int | None:
    """
    Query registration age of a domain in days using standard RDAP protocol.
    Returns None if the check fails.
    """
    if not domain:
        return None
    try:
        url = f"https://rdap.org/domain/{domain.strip().lower()}"
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "SentraSec/1.0 (Crowdsourced Scam Intelligence)"}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                events = data.get("events", [])
                for event in events:
                    if event.get("eventAction") in ("registration", "created"):
                        event_date_str = event.get("eventDate")
                        if event_date_str:
                            clean_date = event_date_str.replace("Z", "+00:00")
                            reg_date = datetime.fromisoformat(clean_date)
                            now = datetime.now(timezone.utc)
                            delta = now - reg_date
                            return delta.days
    except Exception:
        pass
    return None

@router.post("", response_model=APIResponse[ReportResponse], status_code=201)
async def submit_report(body: CreateReportRequest, db: DbDep):
    """
    Submit an anonymous community scam report.
    Contributes to SENTRA's intelligence flywheel. No login required.
    Automatically triggers the non-AI clustering engine in the background.
    """
    if body.isScam and body.domain:
        if is_whitelisted_domain(body.domain):
            raise HTTPException(
                status_code=400,
                detail="Domain resmi terdaftar dalam daftar putih (whitelist) dan tidak dapat dilaporkan sebagai penipuan."
            )
        
        # Check domain age using RDAP
        age_days = get_domain_age_days(body.domain)
        if age_days is not None and age_days > 365:
            raise HTTPException(
                status_code=400,
                detail=f"Domain '{body.domain}' terdeteksi sebagai domain lama terpercaya dan tidak dapat dilaporkan sebagai penipuan."
            )

    clean_phone = normalize_phone(body.phoneNumber)
    clean_bank_acc = normalize_bank_account(body.bankAccount)

    # Build bank_account combined string if both fields are provided
    bank_account_str = None
    if body.bankName and clean_bank_acc:
        bank_account_str = f"{body.bankName} {clean_bank_acc}"
    elif clean_bank_acc:
        bank_account_str = clean_bank_acc

    report = await db.userreport.create(
        data={
            "inputType": body.inputType.value,
            "rawInput": body.rawInput,
            "isScam": body.isScam,
            "notes": body.notes,
            "scamCategory": body.scamCategory,
            "bankName": body.bankName,
            "bankAccount": clean_bank_acc,
            "phoneNumber": clean_phone,
            "domain": body.domain,
            "city": body.city,
            "province": body.province,
        }
    )

    # Fire-and-forget: run clustering engine in background (zero AI calls)
    if body.isScam:
        _fire_clustering(
            db=db,
            report_id=report.id,
            report_text=body.rawInput,
            category=body.scamCategory or "Investasi Mencurigakan",
            bank_account=bank_account_str,
            phone=clean_phone,
            domain=body.domain,
            city=body.city,
            province=body.province,
        )
        logger.info("Report %s submitted — clustering triggered in background.", report.id)

    return APIResponse(data=ReportResponse.model_validate(report, from_attributes=True))


def _fire_clustering(db, report_id: str, report_text: str, category: str,
                     bank_account=None, phone=None, domain=None, city=None, province=None):
    """Schedule the clustering engine as a background task (non-blocking)."""
    import asyncio
    from app.services.clustering_service import run_clustering

    async def _task():
        try:
            await run_clustering(
                db,
                report_id=report_id,
                report_text=report_text,
                category=category,
                bank_account=bank_account,
                phone=phone,
                domain=domain,
                city=city,
                province=province,
            )
        except Exception as exc:
            logger.warning("Background clustering failed for report %s: %s", report_id, exc)

    try:
        asyncio.get_event_loop().call_soon(lambda: asyncio.create_task(_task()))
    except RuntimeError:
        pass  # no running loop during tests — silently skip


@router.get("", response_model=APIResponse[list[ReportResponse]])
async def list_reports(
    db: DbDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List community scam reports (most recent first). No login required."""
    reports = await db.userreport.find_many(
        order={"createdAt": "desc"},
        skip=(page - 1) * per_page,
        take=per_page,
    )
    return APIResponse(
        data=[ReportResponse.model_validate(r, from_attributes=True) for r in reports]
    )
