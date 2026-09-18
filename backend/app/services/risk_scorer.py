"""
Risk scorer v2.1 — combines SENTRA AI score with:
  1. Known scam pattern matching (Prisma intelligence DB)
  2. Intelligence orchestrator signals (OJK, WHOIS, media, community)
  3. GNN graph-based detection (optional, degrades gracefully)
"""
import logging
from typing import Any

from prisma import Prisma

from app.schemas.analysis import RiskLevel, SentraAnalysisResult

logger = logging.getLogger(__name__)

def classify_risk_level(score: int) -> RiskLevel:
    """Map a numeric risk score (0–100) to a RiskLevel enum value."""
    if score <= 20:
        return RiskLevel.SAFE
    elif score <= 40:
        return RiskLevel.LOW
    elif score <= 60:
        return RiskLevel.MEDIUM
    elif score <= 80:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL

# GNN max boost — keep bounded so GNN supplements, never overrides, heuristics
GNN_MAX_BOOST = 25.0

def _get_gnn_service():
    """Lazily import & return the GNN service. Returns None when ML deps are absent."""
    try:
        from ml.gnn_service import gnn_service
        return gnn_service
    except ImportError:
        return None

async def boost_score_from_patterns(
    text: str,
    base_score: int,
    db: Prisma,
    intel=None,  # IntelligenceCheckResult | None
    emotion_signals: list[Any] | None = None,
) -> int:
    """
    Cross-reference extracted text against known scam patterns in the DB,
    apply intelligence signal boosts from the parallel orchestrator,
    add psychological manipulation boosts for detected emotion tactics,
    and add a GNN graph-based boost when available.

    Returns the final boosted score (capped at 100).
    """
    text_lower = text.lower()
    boost = 0.0

    # ── 1. Pattern keyword matching ────────────────────────────────────────
    try:
        patterns = await db.scampattern.find_many()
        for pattern in patterns:
            keywords: list[str] = pattern.keywords or []
            matched = [kw for kw in keywords if kw.lower() in text_lower]
            if matched:
                pattern_boost = pattern.riskWeight * len(matched)
                boost += pattern_boost
                logger.debug(
                    "Pattern '%s' matched %s — boost +%.1f",
                    pattern.name, matched, pattern_boost,
                )
    except Exception as exc:
        logger.warning("Pattern boost failed (non-fatal): %s", exc)

    # ── 2. Intelligence signal boosts (PRD-defined weights) ───────────────
    if intel is not None:
        # OJK illegal → major boost (PRD Check #01)
        if intel.has_illegal_ojk_flag:
            boost += 40.0
            logger.info("OJK illegal flag detected — boost +40")

        # Young domain (PRD Check #15)
        if intel.has_young_domain_flag:
            domain_age = intel.domain_age_days
            if domain_age is not None and domain_age < 30:
                boost += 20.0
                logger.info("Very young domain (%d days) — boost +20", domain_age)
            else:
                boost += 12.0
                logger.info("Young/suspicious domain — boost +12")

        # Negative news coverage (PRD Check #20)
        if intel.has_negative_news:
            news_boost = min(25.0, intel.negative_news_count * 8.0)
            boost += news_boost
            logger.info(
                "%d negative news hits — boost +%.1f",
                intel.negative_news_count, news_boost,
            )

        # Community DB reports (PRD Checks #21-22)
        if intel.has_community_reports:
            community_count = intel.community.community_report_count
            community_boost = min(20.0, community_count * 10.0)
            boost += community_boost
            logger.info(
                "%d community reports — boost +%.1f",
                community_count, community_boost,
            )

        # RAG Semantic Match Boost (gemini-embedding-001 + pgvector)
        if hasattr(intel, "rag_result") and intel.rag_result:
            if getattr(intel.rag_result, "matched_scam_count", 0) > 0 and getattr(intel.rag_result, "top_similarity", 0.0) >= 0.70:
                rag_boost = min(15.0, (intel.rag_result.top_similarity - 0.65) * 50.0)
                boost += rag_boost
                logger.info(
                    "RAG historical scam match (sim=%.2f) — boost +%.1f",
                    intel.rag_result.top_similarity, rag_boost,
                )

    # ── 3. Psychological manipulation boost (Multi-Signal Emotional Pressure) ──
    if emotion_signals:
        detected = [s for s in emotion_signals if getattr(s, "detected", False)]
        detected_count = len(detected)
        if detected_count >= 2:
            base_boost = 18.0 if detected_count >= 4 else (12.0 if detected_count == 3 else 6.0)
            avg_conf = sum(
                (getattr(s, "confidence", 0.70) if getattr(s, "confidence", 0.0) > 0 else 0.70)
                for s in detected
            ) / detected_count
            emotion_boost = round(base_boost * avg_conf, 1)
            boost += emotion_boost
            logger.info(
                "%d emotional manipulation signals detected (avg conf=%.2f) — boost +%.1f",
                detected_count, avg_conf, emotion_boost,
            )

    # ── 4. GNN graph-based boost (optional, non-fatal) ─────────────────────
    try:
        gnn = _get_gnn_service()
        if gnn is not None:
            gnn_boost = await gnn.get_risk_boost(text=text, category=None, db=db)
            if gnn_boost:
                boost += gnn_boost
                logger.info("GNN boost: +%.1f", gnn_boost)
    except Exception as exc:
        logger.warning("GNN boost failed (non-fatal): %s", exc)

    final = min(100, int(base_score + boost))
    logger.info("Risk score: base=%d, boost=+%.1f, final=%d", base_score, boost, final)
    return final

def compute_final_result(
    sentra_result: SentraAnalysisResult,
    boosted_score: int,
) -> tuple[int, RiskLevel, bool]:
    """Merge SENTRA's AI score with pattern + intelligence boost."""
    final_score = max(sentra_result.risk_score, boosted_score)
    final_level = classify_risk_level(final_score)
    safe = final_score < 60
    return final_score, final_level, safe
