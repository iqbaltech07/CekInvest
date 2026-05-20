"""
Intelligence Orchestrator — parallel 23-layer fraud intelligence checks.
PRD Section 5.3 — runs all external checks concurrently before SENTRA analysis.

Implements:
  Category A — Regulasi OJK (checks #01-02 via ojk_service)
  Category C — Data & Intelligence (#15 WHOIS, #16 SSL/hosting, #20 media)
  Category D — Community Intelligence (#21 rekening DB, #22 phone DB)

The result is injected into the SENTRA prompt to give Gemini grounded context.
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import NamedTuple

from prisma import Prisma

from app.services.ojk_service import OjkCheckResult, check_entity
from app.services.whois_service import DomainIntelResult, analyze_domain
from app.services.media_service import NewsItem, search_entity_in_news

logger = logging.getLogger(__name__)

# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class CommunityIntelResult:
    phone_numbers_found: list[str] = field(default_factory=list)    # known scam numbers
    bank_accounts_found: list[str] = field(default_factory=list)    # known scam accounts
    community_report_count: int = 0


@dataclass
class IntelligenceCheckResult:
    """Aggregated result from all parallel intelligence checks."""
    # OJK (checks #01-02)
    ojk_status: str = "TIDAK_DITEMUKAN"
    ojk_entity_name: str | None = None
    ojk_detail: str | None = None

    # Domain intel (checks #15-16)
    domain: str | None = None
    domain_age_days: int | None = None
    domain_country: str | None = None
    is_young_domain: bool = False
    is_suspicious_hosting: bool = False
    domain_notes: list[str] = field(default_factory=list)

    # Media (check #20)
    news_hits: list[dict] = field(default_factory=list)
    negative_news_count: int = 0

    # Community DB (checks #21-22)
    community: CommunityIntelResult = field(default_factory=CommunityIntelResult)

    # Summary flags for risk scoring
    has_illegal_ojk_flag: bool = False
    has_young_domain_flag: bool = False
    has_negative_news: bool = False
    has_community_reports: bool = False

    def to_prompt_context(self) -> str:
        """Format intelligence findings for injection into SENTRA prompt."""
        lines = ["=== DATA INTELIJEN REAL-TIME ==="]

        # OJK
        lines.append(f"\n[REGULASI OJK]")
        lines.append(f"Status OJK: {self.ojk_status}")
        if self.ojk_entity_name:
            lines.append(f"Nama entitas terdeteksi: {self.ojk_entity_name}")
        if self.ojk_detail:
            lines.append(f"Detail: {self.ojk_detail}")

        # Domain
        if self.domain:
            lines.append(f"\n[ANALISIS DOMAIN]")
            lines.append(f"Domain: {self.domain}")
            if self.domain_age_days is not None:
                lines.append(f"Usia domain: {self.domain_age_days} hari")
            if self.domain_country:
                lines.append(f"Negara hosting: {self.domain_country}")
            for note in self.domain_notes:
                lines.append(f"  → {note}")

        # Media
        lines.append(f"\n[PEMBERITAAN MEDIA]")
        if self.news_hits:
            lines.append(f"Ditemukan {len(self.news_hits)} artikel, {self.negative_news_count} negatif:")
            for item in self.news_hits[:5]:
                sentiment = "⚠️ NEGATIF" if item.get("is_negative") else "ℹ️"
                lines.append(f"  {sentiment} [{item.get('source')}] {item.get('title', '')[:100]}")
        else:
            lines.append("Tidak ditemukan pemberitaan terkait.")

        # Community
        if self.community.phone_numbers_found:
            lines.append(f"\n[DATABASE KOMUNITAS — NOMOR TELEPON]")
            lines.append(f"⚠️ {len(self.community.phone_numbers_found)} nomor ditemukan di database scam komunitas")

        if self.community.bank_accounts_found:
            lines.append(f"\n[DATABASE KOMUNITAS — REKENING BANK]")
            lines.append(f"⚠️ {len(self.community.bank_accounts_found)} rekening ditemukan di database scam komunitas")

        lines.append("\n=== GUNAKAN DATA DI ATAS DALAM ANALISISMU ===")
        return "\n".join(lines)


# ── Main Orchestrator ─────────────────────────────────────────────────────────

async def run_parallel_checks(
    content: str,
    input_type: str,
    url: str | None,
    db: Prisma,
    sentra=None,  # Optional SentraService for high-accuracy extraction
) -> IntelligenceCheckResult:
    """
    Run all intelligence checks in parallel (asyncio.gather).
    Returns aggregated IntelligenceCheckResult.
    """
    result = IntelligenceCheckResult()

    # Extract entities from content for OJK check
    entity_names = []
    if sentra:
        try:
            entity_names = await sentra.extract_entities(content)
        except Exception as exc:
            logger.warning("Sentra entity extraction failed, falling back to regex: %s", exc)
    
    if not entity_names:
        entity_names = _extract_entity_names(content)

    phones = _extract_phone_numbers(content)
    bank_accounts = _extract_bank_accounts(content)

    # Build parallel task list
    tasks = []

    # OJK check for each entity
    if entity_names:
        tasks.append(_run_ojk_checks(entity_names[:3], db))  # top 3 to avoid rate limits
    else:
        tasks.append(asyncio.sleep(0))  # placeholder

    # WHOIS for URL analysis
    if url or input_type == "URL":
        target_url = url or _extract_first_url(content)
        if target_url:
            tasks.append(analyze_domain(target_url))
        else:
            tasks.append(asyncio.sleep(0))
    else:
        tasks.append(asyncio.sleep(0))

    # Media search for first entity
    if entity_names:
        tasks.append(search_entity_in_news(entity_names[0]))
    else:
        tasks.append(asyncio.sleep(0))

    # Community DB checks
    tasks.append(_check_community_db(phones, bank_accounts, db))

    # Execute all in parallel
    try:
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as exc:
        logger.warning("Intelligence orchestrator gather failed: %s", exc)
        return result

    # Unpack results safely
    ojk_results = check_results[0] if not isinstance(check_results[0], Exception) else None
    whois_result = check_results[1] if not isinstance(check_results[1], Exception) else None
    news_items = check_results[2] if not isinstance(check_results[2], Exception) else []
    community = check_results[3] if not isinstance(check_results[3], Exception) else CommunityIntelResult()

    # OJK
    if ojk_results and isinstance(ojk_results, dict):
        worst = _pick_worst_ojk(ojk_results)
        result.ojk_status = worst.status
        result.ojk_entity_name = worst.entity_name
        result.ojk_detail = worst.detail
        result.has_illegal_ojk_flag = worst.status == "TERINDIKASI_ILEGAL"

    # Domain
    if whois_result and isinstance(whois_result, DomainIntelResult):
        result.domain = whois_result.domain
        result.domain_age_days = whois_result.domain_age_days
        result.domain_country = whois_result.registrant_country
        result.is_young_domain = whois_result.is_young_domain
        result.is_suspicious_hosting = whois_result.is_suspicious_hosting
        result.domain_notes = list(whois_result.notes)
        result.has_young_domain_flag = whois_result.is_young_domain or whois_result.is_suspicious_hosting

    # Media
    if isinstance(news_items, list) and news_items:
        result.news_hits = [item.__dict__ for item in news_items]
        result.negative_news_count = sum(1 for item in news_items if item.is_negative)
        result.has_negative_news = result.negative_news_count > 0

    # Community
    if isinstance(community, CommunityIntelResult):
        result.community = community
        result.has_community_reports = bool(
            community.phone_numbers_found or community.bank_accounts_found
        )

    logger.info(
        "Intelligence checks complete — OJK: %s | Domain: %s | News: %d | Community: %s",
        result.ojk_status,
        f"{result.domain_age_days}d" if result.domain_age_days else "N/A",
        result.negative_news_count,
        "⚠️" if result.has_community_reports else "clean",
    )
    return result


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _run_ojk_checks(entity_names: list[str], db: Prisma) -> dict:
    """Run OJK check for multiple entities in parallel."""
    results = {}
    tasks = {name: asyncio.create_task(check_entity(name, db)) for name in entity_names}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as exc:
            logger.debug("OJK check failed for '%s': %s", name, exc)
    return results


def _pick_worst_ojk(ojk_results: dict) -> "OjkCheckResult":
    """Pick the most severe OJK status from multiple entity checks."""
    from app.services.ojk_service import OjkCheckResult
    priority = {"TERINDIKASI_ILEGAL": 0, "TIDAK_TERDAFTAR": 1, "TIDAK_DITEMUKAN": 2, "TERDAFTAR": 3}
    worst = max(ojk_results.values(), key=lambda r: -priority.get(r.status, 99))
    return worst


async def _check_community_db(
    phones: list[str], bank_accounts: list[tuple[str, str]], db: Prisma
) -> CommunityIntelResult:
    """Check phones and bank accounts against the community scam database."""
    result = CommunityIntelResult()
    try:
        if phones:
            phone_hits = await db.phonereport.find_many(
                where={"phoneNumber": {"in": phones}}
            )
            result.phone_numbers_found = [h.phoneNumber for h in phone_hits]
            result.community_report_count += len(phone_hits)

        if bank_accounts:
            for bank_name, acct_num in bank_accounts[:5]:
                hit = await db.bankaccountreport.find_first(
                    where={"bankName": bank_name, "accountNumber": acct_num}
                )
                if hit:
                    result.bank_accounts_found.append(f"{bank_name}/{acct_num}")
                    result.community_report_count += 1
    except Exception as exc:
        logger.warning("Community DB check failed (non-fatal): %s", exc)
    return result


def _extract_entity_names(content: str) -> list[str]:
    """Heuristic extraction of potential investment entity names from content."""
    # Common Indonesian words that are NOT entity names but often follow keywords
    # like 'investasi', 'platform', etc.
    STOPWORDS = {
        "yang", "adalah", "merupakan", "dengan", "secara", "untuk", "dalam",
        "dari", "atau", "pada", "juga", "oleh", "bagi", "telah", "bisa",
        "aman", "legal", "resmi", "palsu", "terpercaya", "cepat", "mudah",
        "gratis", "untung", "profit", "dana", "modal", "uang", "saham",
        "crypto", "trading", "bisnis", "usaha", "kami", "anda", "saya",
        "nikmati", "mulai", "wujudkan", "segera", "jangan", "pastikan",
        "investasi", "pengalaman", "tujuan", "finansial", "indonesia",
    }

    # Look for capitalized phrase patterns common in Indonesian investment texts
    patterns = [
        r"\b([A-Z][a-zA-Z0-9]{2,}(?:\s+[A-Z][a-zA-Z0-9]+){0,4})\b",  # Capitalized words (1-5 words)
        r"(?:PT|CV|UD|Koperasi|KOPERASI)\s+([A-Za-z0-9\s\.\-]{3,30})",
        r"(?:perusahaan|investasi|platform|aplikasi)\s+([A-Za-z0-9\s\.\-]{3,30})",
    ]
    
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            cleaned = m.strip().strip(".,- ")
            # Basic validation
            if len(cleaned) < 3:
                continue
            # Skip if it's a known stopword
            if cleaned.lower() in STOPWORDS:
                continue
            # Skip if it's purely generic Indonesian words
            if len(cleaned.split()) == 1 and cleaned.lower() in STOPWORDS:
                continue
            
            found.append(cleaned)

    # Deduplicate and limit
    seen = set()
    unique = []
    for name in found:
        if name.lower() not in seen:
            seen.add(name.lower())
            unique.append(name)
            
    return unique[:5]


def _extract_phone_numbers(content: str) -> list[str]:
    """Extract Indonesian phone numbers from content."""
    # Match common Indonesian phone formats
    pattern = r"(?:0|\+62|62)[\s\-]?(?:8[1-9]|21|22|31)[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{0,4}"
    raw = re.findall(pattern, content)
    # Normalize: strip non-digits, ensure starts with 0
    phones = []
    for p in raw:
        digits = re.sub(r"\D", "", p)
        if digits.startswith("62"):
            digits = "0" + digits[2:]
        if 9 <= len(digits) <= 13:
            phones.append(digits)
    return list(set(phones))


def _extract_bank_accounts(content: str) -> list[tuple[str, str]]:
    """Extract bank name + account number pairs from content."""
    bank_names = [
        "BCA", "BRI", "BNI", "Mandiri", "BSI", "CIMB", "Danamon",
        "Permata", "BTN", "Ocbc", "Maybank", "BRK", "Jago", "Jenius",
    ]
    results = []
    for bank in bank_names:
        # Look for bank name followed by account number (8-16 digits)
        pattern = rf"(?:{bank}|{bank.lower()})[^\d]{{0,20}}(\d{{8,16}})"
        matches = re.findall(pattern, content, re.IGNORECASE)
        for acct in matches:
            results.append((bank, acct))
    return results[:5]


def _extract_first_url(content: str) -> str | None:
    """Extract the first URL from text content."""
    pattern = r"https?://[^\s\]>)\"']+"
    match = re.search(pattern, content)
    return match.group(0) if match else None
