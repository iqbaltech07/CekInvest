"""
Seed script — populates SENTRA's intelligence database with known Indonesian scam patterns.
Uses the Prisma client directly.
Run with: python -m app.seed
"""
import asyncio
import logging

from prisma import Prisma
from prisma.enums import ClusterRiskLevel, RegionalTrend, SpreadLevel

logger = logging.getLogger(__name__)

SCAM_PATTERNS = [
    {
        "name": "Ponzi / Skema Piramida",
        "category": "PONZI",
        "description": "Skema investasi yang membayar investor lama menggunakan uang investor baru, bukan dari keuntungan nyata.",
        "keywords": [
            "return dijamin", "keuntungan pasti", "100% profit", "sistem referral",
            "bonus rekrut", "downline", "passive income tanpa modal",
            "rekrut member", "bayar dari member baru",
        ],
        "riskWeight": 8.0,
    },
    {
        "name": "Robot Trading Palsu",
        "category": "FAKE_ROBOT_TRADING",
        "description": "Klaim menggunakan AI atau bot trading otomatis dengan profit tidak realistis.",
        "keywords": [
            "robot trading", "bot trading", "AI trading otomatis", "profit 50% per bulan",
            "sistem autopilot", "trading tanpa analisa", "hasil trading konsisten",
            "10% per hari", "20% per minggu",
        ],
        "riskWeight": 9.0,
    },
    {
        "name": "Scam Kripto",
        "category": "CRYPTO_SCAM",
        "description": "Penipuan berbasis cryptocurrency seperti pump and dump, fake exchange, atau rug pull.",
        "keywords": [
            "coin baru", "token presale", "rug pull", "pump soon", "x100",
            "moonshot", "kirim crypto dapat lebih banyak", "seed phrase",
            "private key", "connect wallet",
        ],
        "riskWeight": 7.5,
    },
    {
        "name": "Phishing Finansial",
        "category": "PHISHING",
        "description": "Upaya mencuri data finansial atau login melalui tautan atau situs palsu.",
        "keywords": [
            "klik link", "verifikasi akun", "akun dibekukan", "update data",
            "konfirmasi password", "login segera", "OTP jangan dibagi",
            "bit.ly", "tinyurl",
        ],
        "riskWeight": 8.5,
    },
    {
        "name": "Peluang Kerja Palsu",
        "category": "FAKE_JOB",
        "description": "Tawaran kerja dengan penghasilan tidak realistis yang membutuhkan setoran awal.",
        "keywords": [
            "kerja dari rumah", "penghasilan jutaan", "tanpa pengalaman",
            "biaya pendaftaran", "deposit awal", "modal kerja",
            "gaji harian", "part time 5 juta", "WFH tanpa skill",
        ],
        "riskWeight": 6.0,
    },
    {
        "name": "Manipulasi Urgensi",
        "category": "EMOTIONAL_MANIPULATION",
        "description": "Teknik manipulasi psikologis menggunakan rasa urgensi dan kelangkaan palsu.",
        "keywords": [
            "hari ini saja", "slot terbatas", "penawaran berakhir",
            "sekarang atau tidak sama sekali", "jangan sampai menyesal",
            "terbatas!", "hanya untuk 10 orang", "deadline hari ini", "harga naik besok",
        ],
        "riskWeight": 5.0,
    },
    {
        "name": "Investasi Bodong Berlisensi Palsu",
        "category": "FAKE_LICENSE",
        "description": "Klaim memiliki izin OJK atau legalitas palsu untuk membangun kepercayaan.",
        "keywords": [
            "terdaftar OJK", "izin OJK palsu", "legal dan terpercaya",
            "sudah diawasi pemerintah", "bergaransi negara", "sertifikat resmi",
        ],
        "riskWeight": 7.0,
    },
    {
        "name": "Affiliate Scam",
        "category": "AFFILIATE_SCAM",
        "description": "Sistem komisi multi-level yang tidak transparan atau produk tidak jelas.",
        "keywords": [
            "komisi berlevel", "affiliate marketing", "passive income dari referral",
            "sistem binary", "matching bonus", "produk digital tidak jelas",
        ],
        "riskWeight": 5.5,
    },
]

SAMPLE_CLUSTERS = [
    {
        "groupName": "Robot Trading Return Tinggi — Bandung",
        "category": "Robot Trading Scam",
        "riskLevel": ClusterRiskLevel.CRITICAL,
        "totalReports": 184,
        "similarityScore": 0.92,
        "matchedSignals": ["same_bank_account", "guaranteed_profit", "young_domain"],
        "bankAccounts": ["BCA 1234567890", "Mandiri 0987654321"],
        "phoneNumbers": ["081234567890"],
        "domains": ["cuanrobot.vip", "tradingcepat.pro"],
        "dominantRegion": "Bandung",
        "regionalStatus": RegionalTrend.VIRAL,
        "representativeText": "Robot trading profit 50% per bulan dijamin anti rugi. Slot terbatas hari ini saja!",
    },
    {
        "groupName": "Crypto Referral Ponzi — Surabaya",
        "category": "Crypto Scam",
        "riskLevel": ClusterRiskLevel.HIGH,
        "totalReports": 56,
        "similarityScore": 0.78,
        "matchedSignals": ["ponzi_pattern", "high_text_similarity"],
        "bankAccounts": ["BNI 1122334455"],
        "phoneNumbers": ["081199887766"],
        "domains": ["cryptocuan.xyz"],
        "dominantRegion": "Surabaya",
        "regionalStatus": RegionalTrend.RISING,
        "representativeText": "Bonus referral 20% setiap ajak teman join ekosistem crypto terbaru. Passive income nyata!",
    },
    {
        "groupName": "Fake OJK Investment — Jakarta",
        "category": "Investasi Bodong",
        "riskLevel": ClusterRiskLevel.MEDIUM,
        "totalReports": 29,
        "similarityScore": 0.65,
        "matchedSignals": ["fake_authority", "same_phone"],
        "bankAccounts": [],
        "phoneNumbers": ["081200001111"],
        "domains": ["ojk-investasi.com"],
        "dominantRegion": "Jakarta",
        "regionalStatus": RegionalTrend.SPIKING,
        "representativeText": "Investasi aman didukung pemerintah dan diawasi OJK. Bunga 10% per minggu.",
    },
]

SAMPLE_REGIONAL = [
    {
        "region": "Bandung",
        "province": "Jawa Barat",
        "totalReports": 450,
        "currentWeekReports": 120,
        "previousWeekReports": 35,
        "growthPercentage": 242.86,
        "trend": RegionalTrend.VIRAL,
        "spreadLevel": SpreadLevel.HIGH,
        "dominantScamCategory": "Robot Trading Scam",
    },
    {
        "region": "Jakarta",
        "province": "DKI Jakarta",
        "totalReports": 890,
        "currentWeekReports": 210,
        "previousWeekReports": 115,
        "growthPercentage": 82.61,
        "trend": RegionalTrend.SPIKING,
        "spreadLevel": SpreadLevel.NATIONAL,
        "dominantScamCategory": "Investasi Bodong",
    },
    {
        "region": "Surabaya",
        "province": "Jawa Timur",
        "totalReports": 320,
        "currentWeekReports": 65,
        "previousWeekReports": 45,
        "growthPercentage": 44.44,
        "trend": RegionalTrend.RISING,
        "spreadLevel": SpreadLevel.MEDIUM,
        "dominantScamCategory": "Crypto Scam",
    },
    {
        "region": "Medan",
        "province": "Sumatera Utara",
        "totalReports": 150,
        "currentWeekReports": 12,
        "previousWeekReports": 11,
        "growthPercentage": 9.09,
        "trend": RegionalTrend.STABLE,
        "spreadLevel": SpreadLevel.LOW,
        "dominantScamCategory": "Fake Job",
    },
]


async def seed() -> None:
    db = Prisma()
    await db.connect()

    # 1. Scam Patterns
    logger.info("Seeding SENTRA intelligence DB with %d scam patterns...", len(SCAM_PATTERNS))
    for data in SCAM_PATTERNS:
        await db.scampattern.upsert(
            where={"name": data["name"]},
            data={
                "create": data,
                "update": data,
            }
        )
    logger.info("  ✅ Scam patterns seeded.")

    # 2. Scam Clusters
    logger.info("Seeding %d sample scam clusters...", len(SAMPLE_CLUSTERS))
    for data in SAMPLE_CLUSTERS:
        await db.scamcluster.upsert(
            where={"id": f"seed-cluster-{data['dominantRegion']}"},
            data={
                "create": {**data, "id": f"seed-cluster-{data['dominantRegion']}"},
                "update": data,
            }
        )
    logger.info("  ✅ Scam clusters seeded.")

    # 3. Regional Monitoring
    logger.info("Seeding %d regional monitoring records...", len(SAMPLE_REGIONAL))
    for data in SAMPLE_REGIONAL:
        await db.regionalmonitoring.upsert(
            where={"region": data["region"]},
            data={
                "create": data,
                "update": data,
            }
        )
    logger.info("  ✅ Regional monitoring seeded.")

    await db.disconnect()
    logger.info("✅ Full seed complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    asyncio.run(seed())
