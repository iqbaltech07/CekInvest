"""
Database audit script — check data availability for GNN training.
Run: python -m ml.audit_db
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma import Prisma

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def audit_database():
    """Audit database for GNN training readiness."""
    db = Prisma()
    await db.connect()
    
    logger.info("=" * 60)
    logger.info("GNN TRAINING DATA AUDIT")
    logger.info("=" * 60)
    
    # ── Count UserReports ────────────────────────────────────────────────────
    total_reports = await db.userreport.count()
    scam_reports = await db.userreport.count(where={"isScam": True})
    non_scam_reports = total_reports - scam_reports
    
    logger.info("\n[USER REPORTS]")
    logger.info(f"  Total reports: {total_reports}")
    logger.info(f"  Scam reports (label=1): {scam_reports}")
    logger.info(f"  Non-scam reports (label=0): {non_scam_reports}")
    
    if total_reports > 0:
        scam_ratio = scam_reports / total_reports * 100
        logger.info(f"  Scam ratio: {scam_ratio:.1f}%")
    
    # ── Count unique entities ────────────────────────────────────────────────
    reports_with_phone = await db.userreport.count(where={"phoneNumber": {"not": None}})
    reports_with_bank = await db.userreport.count(where={"bankAccount": {"not": None}})
    reports_with_domain = await db.userreport.count(where={"domain": {"not": None}})
    
    logger.info("\n[ENTITY COVERAGE]")
    logger.info(f"  Reports with phone: {reports_with_phone}")
    logger.info(f"  Reports with bank account: {reports_with_bank}")
    logger.info(f"  Reports with domain: {reports_with_domain}")
    
    # ── Count Community DB entries ───────────────────────────────────────────
    phone_reports = await db.phonereport.count()
    bank_reports = await db.bankaccountreport.count()
    
    logger.info("\n[COMMUNITY DATABASE]")
    logger.info(f"  Known scam phones: {phone_reports}")
    logger.info(f"  Known scam bank accounts: {bank_reports}")
    
    # ── Count ScamClusters ───────────────────────────────────────────────────
    clusters = await db.scamcluster.count()
    
    logger.info("\n[SCAM CLUSTERS]")
    logger.info(f"  Total clusters: {clusters}")
    
    if clusters > 0:
        sample = await db.scamcluster.find_first()
        if sample:
            logger.info(f"  Sample cluster: {sample.groupName}")
            logger.info(f"    - Total reports: {sample.totalReports}")
            logger.info(f"    - Risk level: {sample.riskLevel}")
            logger.info(f"    - Bank accounts: {len(sample.bankAccounts)}")
            logger.info(f"    - Phones: {len(sample.phoneNumbers)}")
            logger.info(f"    - Domains: {len(sample.domains)}")
    
    # ── Count Analyses ───────────────────────────────────────────────────────
    analyses = await db.analysis.count()
    analyses_with_hash = await db.analysis.count(where={"inputHash": {"not": None}})
    
    logger.info("\n[ANALYSES]")
    logger.info(f"  Total analyses: {analyses}")
    logger.info(f"  With input hash (dedup): {analyses_with_hash}")
    
    # ── Training Readiness Assessment ────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING READINESS ASSESSMENT")
    logger.info("=" * 60)
    
    min_recommended = 500
    
    if total_reports >= min_recommended:
        logger.info(f"✅ Sufficient data for GNN training ({total_reports} >= {min_recommended})")
    elif total_reports >= 100:
        logger.warning(f"⚠️  Limited data ({total_reports} < {min_recommended})")
        logger.warning("   Training possible but may overfit. Consider data augmentation.")
    else:
        logger.error(f"❌ Insufficient data ({total_reports} < 100)")
        logger.error("   Need more UserReports before training.")
        logger.error("   Run seed script: python -m app.seed")
    
    # Entity connectivity check
    entity_coverage = reports_with_phone + reports_with_bank + reports_with_domain
    if total_reports > 0:
        connectivity = entity_coverage / (total_reports * 3) * 100
        logger.info(f"\nEntity connectivity: {connectivity:.1f}%")
        if connectivity > 50:
            logger.info("✅ Good graph connectivity")
        else:
            logger.warning("⚠️  Low connectivity — many isolated nodes")
    
    # ── Recommendations ──────────────────────────────────────────────────────
    logger.info("\n[RECOMMENDATIONS]")
    
    if total_reports < min_recommended:
        logger.info("1. Run seed script to populate sample data:")
        logger.info("   python -m app.seed")
        logger.info("2. Encourage community reports via frontend")
        logger.info("3. Use pseudo-labels from ScamCluster results")
    
    if clusters == 0 and total_reports > 0:
        logger.info("4. Run clustering engine to create initial clusters")
    
    await db.disconnect()
    logger.info("\n✅ Audit complete.")


if __name__ == "__main__":
    asyncio.run(audit_database())
