"""
WHOIS / Domain Intelligence Service.
PRD Checks implemented:
  #15 — Analisis usia domain website (domain < 90 days = red flag)
  #16 — Analisis SSL dan hosting (anonymous hosting / tax haven country)

Strategy:
  1. RDAP (rdap.org) — primary, free, ICANN standard, no CLI dependency
  2. python-whois — fallback
  3. Redis cache (TTL: 24hrs)
"""
import logging
import re
from datetime import datetime, timezone
from typing import NamedTuple
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.cache_service import cache_get, cache_set, make_whois_key

logger = logging.getLogger(__name__)

_SUSPICIOUS_COUNTRIES = {
    "SC", "VU", "PA", "BZ", "KY", "VG", "AG", "LC", "VC",
    "RU", "UA", "CN", "NG", "RO",
}

_SUSPICIOUS_REGISTRARS = {
    "namecheap", "enom", "publicdomainregistry", "godaddy private",
    "domains by proxy", "whoisguard", "withheldforprivacy",
}

class DomainIntelResult(NamedTuple):
    domain: str
    domain_age_days: int | None
    registrar: str | None
    registrant_country: str | None
    is_young_domain: bool
    is_suspicious_hosting: bool
    whois_available: bool
    notes: list[str]

async def analyze_domain(url: str) -> DomainIntelResult:
    domain = _extract_domain(url)
    if not domain:
        return DomainIntelResult(
            domain=url, domain_age_days=None, registrar=None,
            registrant_country=None, is_young_domain=False,
            is_suspicious_hosting=False, whois_available=False,
            notes=["Tidak dapat mengekstrak domain dari URL ini."],
        )

    cache_key = make_whois_key(domain)
    cached = await cache_get(cache_key)
    if cached:
        return DomainIntelResult(**cached)

    result = await _query_rdap(domain)
    if result is None:
        result = await _query_python_whois(domain)
    
    if result is None:
        result = DomainIntelResult(
            domain=domain, domain_age_days=None, registrar=None,
            registrant_country=None, is_young_domain=False,
            is_suspicious_hosting=False, whois_available=False,
            notes=["Informasi WHOIS tidak tersedia."],
        )

    await cache_set(cache_key, result._asdict(), ttl_seconds=86400)
    return result

async def _query_rdap(domain: str) -> DomainIntelResult | None:
    try:
        rdap_url = f"https://rdap.org/domain/{domain}"
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(rdap_url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return _parse_rdap_response(domain, data)
    except Exception:
        return None

def _parse_rdap_response(domain: str, data: dict) -> DomainIntelResult:
    notes = []
    age_days = None
    events = data.get("events", [])
    for event in events:
        if event.get("eventAction") == "registration":
            try:
                reg_date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - reg_date).days
            except Exception: pass

    registrar = None
    entities = data.get("entities", [])
    for entity in entities:
        if "registrar" in entity.get("roles", []):
            vcard = entity.get("vcardArray", [])
            if vcard and len(vcard) > 1:
                for item in vcard[1]:
                    if item[0] == "fn":
                        registrar = item[3]
                        break

    country = None
    for entity in entities:
        if "registrant" in entity.get("roles", []):
            vcard = entity.get("vcardArray", [])
            if vcard and len(vcard) > 1:
                for item in vcard[1]:
                    if item[0] == "adr":
                        addr = item[3]
                        if isinstance(addr, list) and len(addr) >= 7:
                            country = addr[6]

    is_young = age_days is not None and age_days < settings.DOMAIN_AGE_RED_FLAG_DAYS
    is_suspicious_host = (
        (country and country.upper() in _SUSPICIOUS_COUNTRIES) or
        (registrar and any(s in registrar.lower() for s in _SUSPICIOUS_REGISTRARS))
    )

    if is_young: notes.append(f"⚠️ Domain baru: {age_days} hari.")
    if is_suspicious_host: notes.append("⚠️ Hosting berisiko tinggi.")

    return DomainIntelResult(
        domain=domain, domain_age_days=age_days, registrar=registrar,
        registrant_country=country, is_young_domain=is_young,
        is_suspicious_hosting=is_suspicious_host, whois_available=True,
        notes=notes
    )

async def _query_python_whois(domain: str) -> DomainIntelResult | None:
    try:
        import whois
        import asyncio
        w = await asyncio.to_thread(whois.whois, domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list): creation_date = creation_date[0]
        
        age_days = None
        if creation_date:
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - creation_date).days

        is_young = age_days is not None and age_days < settings.DOMAIN_AGE_RED_FLAG_DAYS
        is_suspicious_host = (
            (w.country and w.country.upper() in _SUSPICIOUS_COUNTRIES) or
            (w.registrar and any(s in w.registrar.lower() for s in _SUSPICIOUS_REGISTRARS))
        )

        return DomainIntelResult(
            domain=domain, domain_age_days=age_days, registrar=w.registrar,
            registrant_country=w.country, is_young_domain=is_young,
            is_suspicious_hosting=is_suspicious_host, whois_available=True,
            notes=[]
        )
    except Exception: return None

def _extract_domain(url: str) -> str | None:
    try:
        if not url.startswith(("http://", "https://")): url = "https://" + url
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return re.sub(r"^www\.", "", hostname)
    except Exception: return None
