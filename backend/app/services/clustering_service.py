"""
Non-AI Scam Clustering & Regional Monitoring Engine.

100% rule-based — zero calls to Gemini or any generative AI.
Implements every detection rule from non_ai_scam_clustering_prompt.md:
  1. Exact-match signals  (bank account / phone / domain)
  2. Behavioral keywords  (urgency / guaranteed profit / ponzi / fake authority)
  3. Domain signals       (suspicious TLD / young domain)
  4. Text similarity      (TF-IDF + cosine similarity)
  5. Clustering           (find-or-create cluster, merge matching reports)
  6. Regional monitoring  (weekly growth, trend status, spread level)

Entry-point: run_clustering()
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Optional

from prisma import Prisma

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# Exact-match signal weights
SIGNAL_WEIGHTS = {
    "same_bank_account": 40,
    "same_phone":        30,
    "same_domain":       25,
    "same_email":        20,
}

# Behavioral keyword groups
BEHAVIORAL_KEYWORDS = {
    "fake_urgency": {
        "keywords": ["slot terbatas", "hari ini saja", "closing malam ini", "jangan sampai terlambat"],
        "score": 10,
        "signal": "fake_urgency",
    },
    "guaranteed_profit": {
        "keywords": ["profit dijamin", "anti rugi", "cuan pasti", "return tetap"],
        "score": 15,
        "signal": "guaranteed_profit",
    },
    "ponzi_referral": {
        "keywords": ["cari member", "bonus referral", "passive income downline"],
        "score": 15,
        "signal": "ponzi_pattern",
    },
    "fake_authority": {
        "keywords": ["resmi ojk", "didukung pemerintah", "artis terkenal"],
        "score": 10,
        "signal": "fake_authority",
    },
}

# Suspicious domain TLDs
SUSPICIOUS_TLDS = {".vip", ".xyz", ".pro", ".top"}

# Similarity → score mapping (descending threshold order)
SIMILARITY_THRESHOLDS = [
    (0.8, 25, "high_text_similarity"),
    (0.6, 15, "medium_text_similarity"),
    (0.4,  8, "low_text_similarity"),
]

# Risk level score boundaries
RISK_BOUNDARIES = [
    (81, "CRITICAL"),
    (61, "HIGH"),
    (31, "MEDIUM"),
    (0,  "LOW"),
]

# Regional trend thresholds (growth %)
TREND_THRESHOLDS = [
    (150, "VIRAL"),
    (50,  "SPIKING"),
    (10,  "RISING"),
    (0,   "STABLE"),
]

# Spread level city count boundaries
SPREAD_BOUNDARIES = [
    (10, "NATIONAL"),   # > 10 provinces → NATIONAL (approximated by city count here)
    (5,  "HIGH"),
    (2,  "MEDIUM"),
    (0,  "LOW"),
]


# ── Scoring Engine ────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def score_signals(
    report_text: str,
    domain: Optional[str],
    phone: Optional[str],
    bank_account: Optional[str],
    domain_age_days: Optional[int],
    # existing clusters to compare against
    existing_texts: list[str],
) -> tuple[int, list[str], float]:
    """
    Compute the total scam signal score for one report.

    Returns:
        (total_score, matched_signals, best_text_similarity)
    """
    score = 0
    matched: list[str] = []
    norm = _normalize_text(report_text)

    # 1. Behavioral keywords
    for group in BEHAVIORAL_KEYWORDS.values():
        for kw in group["keywords"]:
            if kw in norm:
                score += group["score"]
                sig = group["signal"]
                if sig not in matched:
                    matched.append(sig)
                break  # one hit per group is enough

    # 2. Domain TLD signal
    if domain:
        d = domain.lower()
        for tld in SUSPICIOUS_TLDS:
            if d.endswith(tld):
                score += 10
                matched.append("suspicious_tld")
                break

    # 3. Young domain signal
    if domain_age_days is not None and domain_age_days < 90:
        score += 15
        matched.append("young_domain")

    best_sim = 0.0
    sim_signal: Optional[str] = None
    if existing_texts:
        best_sim = _best_text_similarity(norm, existing_texts)

        for threshold, sim_score, sig in SIMILARITY_THRESHOLDS:
            if best_sim >= threshold:
                score += sim_score
                sim_signal = sig
                matched.append(sig)
                break

    return min(score, 100), matched, best_sim


def _best_text_similarity(text: str, existing_texts: list[str]) -> float:
    """Use TF-IDF when installed; fall back to deterministic string similarity."""
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = existing_texts + [text]
        vec = TfidfVectorizer(min_df=1, ngram_range=(1, 2)).fit_transform(corpus)
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()
        return float(np.max(sims))
    except ImportError:
        return max(SequenceMatcher(None, text, candidate).ratio() for candidate in existing_texts)


def classify_risk_level(score: int) -> str:
    """Map numeric score → risk level string per spec table."""
    for threshold, level in RISK_BOUNDARIES:
        if score >= threshold:
            return level
    return "LOW"


def _build_group_name(category: str, dominant_region: Optional[str]) -> str:
    """Format: [scam category] + [dominant region]."""
    if dominant_region:
        return f"{category} — {dominant_region}"
    return category


# ── Cluster Find-or-Create ────────────────────────────────────────────────────

async def find_or_create_cluster(
    db: Prisma,
    *,
    report_id: str,
    report_text: str,
    category: str,
    domain: Optional[str],
    phone: Optional[str],
    bank_account: Optional[str],
    domain_age_days: Optional[int],
    city: Optional[str],
    province: Optional[str],
) -> dict:
    """
    Find the best matching ScamCluster or create a new one.
    Returns a dict summarising the cluster result.
    """
    norm_text = _normalize_text(report_text)

    # Load all existing clusters (we expect < thousands; acceptable for now)
    clusters = await db.scamcluster.find_many(
        include={"analyses": False},
    )

    best_cluster = None
    best_score = -1
    best_signals: list[str] = []
    best_sim = 0.0

    for cluster in clusters:
        signals: list[str] = []

        # Exact-match signals
        if bank_account and bank_account in cluster.bankAccounts:
            signals.append("same_bank_account")
        if phone and phone in cluster.phoneNumbers:
            signals.append("same_phone")
        if domain and domain.lower() in [d.lower() for d in cluster.domains]:
            signals.append("same_domain")

        # Text similarity against cluster's representative text
        rep_texts = [cluster.representativeText] if cluster.representativeText else []
        score, sig_extra, sim = score_signals(
            report_text=report_text,
            domain=domain,
            phone=phone,
            bank_account=bank_account,
            domain_age_days=domain_age_days,
            existing_texts=rep_texts,
        )
        signals.extend(s for s in sig_extra if s not in signals)

        # Total weight: exact matches carry heavy weight
        exact_score = sum(SIGNAL_WEIGHTS.get(s, 0) for s in signals if s in SIGNAL_WEIGHTS)
        total = exact_score + score

        if signals and total > best_score:
            best_cluster = cluster
            best_score = total
            best_signals = signals
            best_sim = sim

    # Threshold to merge: at least one strong signal OR high similarity
    has_strong_signal = any(s in best_signals for s in SIGNAL_WEIGHTS)
    merge_threshold = 0.6

    if best_cluster and (has_strong_signal or best_sim >= merge_threshold):
        # Merge into existing cluster
        new_total = best_cluster.totalReports + 1
        new_avg_sim = (best_cluster.similarityScore * best_cluster.totalReports + best_sim) / new_total
        new_risk = classify_risk_level(best_score)

        # Upsert contact identifiers
        new_banks = list(set(best_cluster.bankAccounts + ([bank_account] if bank_account else [])))
        new_phones = list(set(best_cluster.phoneNumbers + ([phone] if phone else [])))
        new_domains = list(set(best_cluster.domains + ([domain.lower()] if domain else [])))
        new_signals = list(set(best_cluster.matchedSignals + best_signals))

        updated = await db.scamcluster.update(
            where={"id": best_cluster.id},
            data={
                "totalReports": new_total,
                "similarityScore": new_avg_sim,
                "riskLevel": new_risk,
                "bankAccounts": new_banks,
                "phoneNumbers": new_phones,
                "domains": new_domains,
                "matchedSignals": new_signals,
                "dominantRegion": city or best_cluster.dominantRegion,
            },
        )

        # Create membership
        try:
            await db.clustermembership.create(
                data={"clusterId": best_cluster.id, "reportId": report_id, "similarity": best_sim}
            )
        except Exception:
            pass  # duplicate membership — ignore

        logger.info("Merged report %s into cluster %s (risk=%s)", report_id, best_cluster.id, new_risk)
        return _cluster_to_dict(updated, best_signals, best_sim)

    else:
        # Create brand-new cluster
        _, init_signals, _ = score_signals(
            report_text=report_text,
            domain=domain,
            phone=phone,
            bank_account=bank_account,
            domain_age_days=domain_age_days,
            existing_texts=[],
        )
        init_score = sum(SIGNAL_WEIGHTS.get(s, 0) for s in init_signals)
        init_risk = classify_risk_level(init_score)
        group_name = _build_group_name(category, city)

        new_cluster = await db.scamcluster.create(
            data={
                "groupName": group_name,
                "category": category,
                "riskLevel": init_risk,
                "totalReports": 1,
                "similarityScore": 0.0,
                "matchedSignals": init_signals,
                "bankAccounts": [bank_account] if bank_account else [],
                "phoneNumbers": [phone] if phone else [],
                "domains": [domain.lower()] if domain else [],
                "dominantRegion": city,
                "representativeText": norm_text[:2000],
            },
        )
        try:
            await db.clustermembership.create(
                data={"clusterId": new_cluster.id, "reportId": report_id, "similarity": 0.0}
            )
        except Exception:
            pass

        logger.info("Created new cluster %s (risk=%s) for report %s", new_cluster.id, init_risk, report_id)
        return _cluster_to_dict(new_cluster, init_signals, 0.0)


def _cluster_to_dict(cluster, signals: list[str], similarity: float) -> dict:
    return {
        "cluster_id": cluster.id,
        "group_name": cluster.groupName,
        "risk_level": cluster.riskLevel if isinstance(cluster.riskLevel, str) else cluster.riskLevel.value,
        "total_reports": cluster.totalReports,
        "similarity_percentage": round(similarity * 100, 1),
        "matched_signals": signals,
        "dominant_region": cluster.dominantRegion,
    }


# ── Regional Monitoring ───────────────────────────────────────────────────────

def _classify_trend(growth_pct: float) -> str:
    for threshold, status in TREND_THRESHOLDS:
        if growth_pct > threshold:
            return status
    return "STABLE"


def _classify_spread(city_count: int) -> str:
    for threshold, level in SPREAD_BOUNDARIES:
        if city_count > threshold:
            return level
    return "LOW"


async def update_regional_stats(
    db: Prisma,
    *,
    city: Optional[str],
    province: Optional[str],
    scam_category: str,
) -> Optional[dict]:
    """
    Recalculate regional monitoring snapshot for the given city.
    Uses current-week vs previous-week Analysis counts as growth proxy.
    """
    if not city:
        return None

    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    two_weeks_start = now - timedelta(days=14)

    # Count memberships per region by looking at cluster dominant regions
    # (We approximate weekly counts via ScamCluster.updatedAt / createdAt)
    all_clusters = await db.scamcluster.find_many(
        where={"dominantRegion": city},
    )

    current_week = sum(
        1 for c in all_clusters
        if c.updatedAt and c.updatedAt >= week_start
    )
    previous_week = sum(
        1 for c in all_clusters
        if c.updatedAt and two_weeks_start <= c.updatedAt < week_start
    )
    total = sum(c.totalReports for c in all_clusters)

    if previous_week > 0:
        growth_pct = ((current_week - previous_week) / previous_week) * 100
    elif current_week > 0:
        growth_pct = 100.0
    else:
        growth_pct = 0.0

    trend = _classify_trend(growth_pct)

    # Spread: how many distinct regions report same category
    cities_with_category = await db.scamcluster.find_many(
        where={"category": scam_category},
    )
    city_count = len({c.dominantRegion for c in cities_with_category if c.dominantRegion})
    spread = _classify_spread(city_count)

    # Dominant category in city
    category_counts: dict[str, int] = {}
    for c in all_clusters:
        category_counts[c.category] = category_counts.get(c.category, 0) + c.totalReports
    dominant_category = max(category_counts, key=category_counts.get) if category_counts else scam_category

    # Upsert regional record
    regional = await db.regionalmonitoring.upsert(
        where={"region": city},
        data={
            "create": {
                "region": city,
                "province": province,
                "totalReports": total,
                "currentWeekReports": current_week,
                "previousWeekReports": previous_week,
                "growthPercentage": round(growth_pct, 2),
                "trend": trend,
                "spreadLevel": spread,
                "dominantScamCategory": dominant_category,
            },
            "update": {
                "province": province,
                "totalReports": total,
                "currentWeekReports": current_week,
                "previousWeekReports": previous_week,
                "growthPercentage": round(growth_pct, 2),
                "trend": trend,
                "spreadLevel": spread,
                "dominantScamCategory": dominant_category,
            },
        },
    )

    logger.info(
        "Regional stats updated: city=%s growth=%.1f%% trend=%s spread=%s",
        city, growth_pct, trend, spread,
    )
    return {
        "region": regional.region,
        "province": regional.province,
        "total_reports": regional.totalReports,
        "growth_percentage": regional.growthPercentage,
        "trend": regional.trend if isinstance(regional.trend, str) else regional.trend.value,
        "spread_level": regional.spreadLevel if isinstance(regional.spreadLevel, str) else regional.spreadLevel.value,
        "dominant_scam_category": regional.dominantScamCategory,
    }


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_clustering(
    db: Prisma,
    *,
    report_id: str,
    report_text: str,
    category: str = "Investasi Mencurigakan",
    domain: Optional[str] = None,
    phone: Optional[str] = None,
    bank_account: Optional[str] = None,
    domain_age_days: Optional[int] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
) -> dict:
    """
    Main clustering pipeline — called after every Analysis is persisted.
    Returns full clustering output matching the spec JSON format.
    """
    try:
        cluster_result = await find_or_create_cluster(
            db,
            report_id=report_id,
            report_text=report_text,
            category=category,
            domain=domain,
            phone=phone,
            bank_account=bank_account,
            domain_age_days=domain_age_days,
            city=city,
            province=province,
        )
    except Exception as exc:
        logger.error("Clustering find_or_create failed: %s", exc, exc_info=True)
        return {}

    try:
        regional_result = await update_regional_stats(
            db,
            city=city,
            province=province,
            scam_category=category,
        )
    except Exception as exc:
        logger.error("Regional stats update failed: %s", exc, exc_info=True)
        regional_result = None

    output = {
        "input_category": category,
        "scam_groups": [
            {
                "group_name": cluster_result.get("group_name"),
                "similarity_percentage": cluster_result.get("similarity_percentage", 0),
                "risk_level": cluster_result.get("risk_level"),
                "regional_status": {
                    "dominant_region": cluster_result.get("dominant_region"),
                    "regional_trend": regional_result.get("trend") if regional_result else "STABLE",
                    "regional_growth_percentage": regional_result.get("growth_percentage", 0) if regional_result else 0,
                    "spread_level": regional_result.get("spread_level") if regional_result else "LOW",
                },
                "total_similar_reports": cluster_result.get("total_reports", 1),
                "matched_signals": cluster_result.get("matched_signals", []),
            }
        ],
        "regional_monitoring": {
            "most_viral_regions": (
                [
                    {
                        "region": regional_result["region"],
                        "dominant_scam": regional_result.get("dominant_scam_category"),
                        "growth_percentage": regional_result.get("growth_percentage", 0),
                        "status": regional_result.get("trend"),
                    }
                ]
                if regional_result and regional_result.get("trend") in ("SPIKING", "VIRAL")
                else []
            ),
        },
    }

    logger.info(
        "Clustering complete: cluster=%s risk=%s region_trend=%s",
        cluster_result.get("cluster_id"),
        cluster_result.get("risk_level"),
        regional_result.get("trend") if regional_result else "N/A",
    )
    return output
