"""
Vector Store Service for CekInvest.
Manages PostgreSQL pgvector tables for dense semantic search and RAG retrieval.
"""
import logging
import json
from typing import Any, List, Optional
from prisma import Prisma

logger = logging.getLogger(__name__)

# Default knowledge base documents containing authoritative OJK rules and Indonesian financial regulations
INITIAL_KNOWLEDGE_DOCS = [
    {
        "id": "ojk_rule_01",
        "title": "Larangan Klaim Jaminan Keuntungan Pasti (Fixed Return)",
        "content": (
            "Berdasarkan UU Pasar Modal No. 8 Tahun 1995 dan regulasi Otoritas Jasa Keuangan (OJK), "
            "setiap lembaga keuangan atau entitas investasi DILARANG KERAS menjanjikan keuntungan pasti (fixed return) "
            "atau imbal hasil tanpa risiko. Setiap investasi berbanding lurus antara risiko dan potensi keuntungan (high risk, high return). "
            "Klaim profit harian di atas 1% atau profit bulanan di atas 3-5% tanpa risiko dipastikan merupakan indikasi skema Ponzi atau investasi bodong."
        ),
        "source": "OJK & UU Pasar Modal",
        "category": "Regulasi OJK",
    },
    {
        "id": "ojk_rule_02",
        "title": "Regulasi Robot Trading dan Penasihat Berjangka Bappebti",
        "content": (
            "Aktivitas perdagangan berjangka, forex, crypto, dan robot trading di Indonesia di bawah pengawasan Bappebti "
            "(Kementerian Perdagangan), bukan hanya izin SIUP/NIB. Penyelenggara Expert Advisor (EA/Robot Trading) wajib memiliki "
            "izin resmi dan broker yang digunakan harus broker lokal terdaftar Bappebti. Menggunakan broker luar negeri ilegal tanpa izin "
            "dengan dalih server luar negeri adalah modus umum penipuan robot trading bodong."
        ),
        "source": "Bappebti & Satgas PASTI",
        "category": "Trading & Forex",
    },
    {
        "id": "ojk_rule_03",
        "title": "Skema Ponzi dan Modus Member-Get-Member (Piramida)",
        "content": (
            "Skema Ponzi adalah modus penipuan di mana keuntungan investor lama dibayarkan dari uang setoran investor baru, "
            "bukan dari hasil kegiatan usaha atau perdagangan riil. Ciri utama meliputi: bonus referral bertingkat (multi-level), "
            "kewajiban merekrut anggota untuk mencairkan dana (lock-up modal), serta kesulitan penarikan (WD) dengan alasan perbaikan sistem atau pajak tambahan."
        ),
        "source": "Satgas Waspada Investasi (PASTI)",
        "category": "Modus Penipuan",
    },
    {
        "id": "ojk_rule_04",
        "title": "Larangan Transfer Dana Investasi ke Rekening Pribadi / Perorangan",
        "content": (
            "Perusahaan investasi, sekuritas, manajer investasi, atau platform p2p lending yang legal dan terdaftar OJK "
            "TIDAK PERNAH menggunakan rekening bank atas nama pribadi (perorangan) untuk menampung dana investasi nasabah. "
            "Dana wajib disetorkan ke Rekening Dana Nasabah (RDN) atau rekening giro resmi atas nama perseroan (PT) yang telah diverifikasi bank kustodian."
        ),
        "source": "Peraturan OJK Transaksi Keuangan",
        "category": "Perbankan & Rekening",
    },
    {
        "id": "ojk_rule_05",
        "title": "Phishing Domain dan Modus Akun Telegram Titip Dana",
        "content": (
            "Penipuan berkedok 'Titip Dana Trading' atau 'Arisan Online' melalui grup Telegram/WhatsApp sering kali memalsukan "
            "identitas perusahaan legal dengan menambahkan kata resmi, official, atau vip. Pelaku menggunakan foto profil figur publik "
            "dan testimoni editan. Pengguna diminta transfer sejumlah uang dan dijanjikan cair dalam hitungan jam. Ketika diminta cair, "
            "pelaku akan meminta biaya admin atau pajak pencairan palsu."
        ),
        "source": "Kementerian Komdigi & OJK",
        "category": "Social Engineering",
    },
]


class VectorStoreService:
    """Service managing pgvector tables and vector similarity searches."""

    @staticmethod
    async def init_vector_tables(db: Prisma) -> None:
        """Ensure pgvector extension exists and schema tables are created."""
        try:
            # 1. Enable extension
            await db.execute_raw("CREATE EXTENSION IF NOT EXISTS vector;")

            # 2. Table for User Reports embeddings
            await db.execute_raw("""
                CREATE TABLE IF NOT EXISTS report_embeddings (
                    id VARCHAR(64) PRIMARY KEY,
                    report_id VARCHAR(64) NOT NULL,
                    raw_input TEXT NOT NULL,
                    is_scam BOOLEAN NOT NULL,
                    scam_category VARCHAR(128),
                    embedding vector(768) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Table for Knowledge Base OJK & Legal reference docs
            await db.execute_raw("""
                CREATE TABLE IF NOT EXISTS rag_knowledge_base (
                    id VARCHAR(64) PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    source VARCHAR(128) NOT NULL,
                    category VARCHAR(128) NOT NULL,
                    embedding vector(768) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Ensure updated_at column exists for older installations
            try:
                await db.execute_raw("""
                    ALTER TABLE rag_knowledge_base
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
                """)
            except Exception:
                pass

            # 4. Indexes for fast vector cosine similarity search
            try:
                await db.execute_raw("""
                    CREATE INDEX IF NOT EXISTS report_embeddings_vec_idx 
                    ON report_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
                """)
                await db.execute_raw("""
                    CREATE INDEX IF NOT EXISTS rag_knowledge_vec_idx 
                    ON rag_knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 5);
                """)
            except Exception as idx_exc:
                # ivfflat index can require minimum rows before creation in some pgvector versions; non-fatal
                logger.debug("Vector index creation notice (non-fatal): %s", idx_exc)

            logger.info("✅ pgvector tables initialized successfully.")

        except Exception as exc:
            logger.error("Error initializing pgvector tables: %s", exc)
            raise exc

    @staticmethod
    async def upsert_report_embedding(
        db: Prisma,
        report_id: str,
        raw_input: str,
        is_scam: bool,
        scam_category: Optional[str],
        embedding: list[float],
    ) -> None:
        """Inserts or updates a dense vector embedding for a user report."""
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        query = """
            INSERT INTO report_embeddings (id, report_id, raw_input, is_scam, scam_category, embedding)
            VALUES ($1, $2, $3, $4, $5, $6::vector)
            ON CONFLICT (id) DO UPDATE SET
                raw_input = EXCLUDED.raw_input,
                is_scam = EXCLUDED.is_scam,
                scam_category = EXCLUDED.scam_category,
                embedding = EXCLUDED.embedding;
        """
        await db.execute_raw(query, f"emb_{report_id}", report_id, raw_input, is_scam, scam_category or "General", vec_str)

    @staticmethod
    async def search_similar_reports(
        db: Prisma,
        query_embedding: list[float],
        limit: int = 4,
        min_similarity: float = 0.50,
    ) -> list[dict[str, Any]]:
        """
        Finds reports with highest cosine similarity using pgvector <=> operator.
        Returns list of matched reports with similarity scores (0.0 to 1.0).
        """
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        query = """
            SELECT report_id, raw_input, is_scam, scam_category,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM report_embeddings
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $2;
        """
        rows = await db.query_raw(query, vec_str, limit)
        results = []
        for r in rows:
            sim = float(r.get("similarity", 0.0))
            if sim >= min_similarity:
                results.append({
                    "report_id": r.get("report_id"),
                    "raw_input": r.get("raw_input"),
                    "is_scam": bool(r.get("is_scam")),
                    "category": r.get("scam_category"),
                    "similarity": round(sim, 3),
                })
        return results

    @staticmethod
    async def search_knowledge_base(
        db: Prisma,
        query_embedding: list[float],
        limit: int = 2,
        min_similarity: float = 0.45,
    ) -> list[dict[str, Any]]:
        """Finds most relevant OJK regulatory knowledge articles via cosine similarity."""
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        query = """
            SELECT id, title, content, source, category,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM rag_knowledge_base
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $2;
        """
        rows = await db.query_raw(query, vec_str, limit)
        results = []
        for r in rows:
            sim = float(r.get("similarity", 0.0))
            if sim >= min_similarity:
                results.append({
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "content": r.get("content"),
                    "source": r.get("source"),
                    "category": r.get("category"),
                    "similarity": round(sim, 3),
                })
        return results

    @staticmethod
    async def seed_knowledge_base_if_empty(db: Prisma, embedding_svc) -> int:
        """Seed default OJK and regulatory reference documents if the table is empty."""
        try:
            count_res = await db.query_raw("SELECT COUNT(*) as count FROM rag_knowledge_base;")
            count = int(count_res[0].get("count", 0)) if count_res else 0
            if count > 0:
                return count

            logger.info("Seeding OJK knowledge base with authoritative regulatory articles...")
            inserted = 0
            for doc in INITIAL_KNOWLEDGE_DOCS:
                embed_text = f"{doc['title']}. {doc['content']}"
                vec = await embedding_svc.embed_text(embed_text)
                vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                await db.execute_raw(
                    """
                    INSERT INTO rag_knowledge_base (id, title, content, source, category, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6::vector)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    doc["id"], doc["title"], doc["content"], doc["source"], doc["category"], vec_str
                )
                inserted += 1

            logger.info("✅ Seeded %d OJK regulatory articles into rag_knowledge_base", inserted)
            return inserted
        except Exception as exc:
            logger.warning("Failed to seed knowledge base: %s", exc)
            return 0

    @staticmethod
    async def sync_scam_patterns_to_knowledge_base(db: Prisma, embedding_svc) -> int:
        """
        Migrates all ScamPattern records from the `scam_patterns` table into the
        `rag_knowledge_base` pgvector table as dense embeddings.

        This replaces static keyword matching with semantic retrieval:
        - Typos, slang, and paraphrases of scam keywords are still matched
        - Each pattern becomes a 768-dim vector searchable via cosine similarity
        - Uses upsert (ON CONFLICT) so re-running is always safe and idempotent
        """
        try:
            patterns = await db.scampattern.find_many()
            if not patterns:
                logger.info("No ScamPatterns found to sync.")
                return 0

            logger.info(
                "Syncing %d ScamPatterns to rag_knowledge_base as semantic embeddings...",
                len(patterns),
            )
            synced = 0
            for pattern in patterns:
                # Build a comprehensive description combining all pattern fields
                keyword_list = ", ".join(pattern.keywords[:20]) if pattern.keywords else "(no keywords)"
                embed_text = (
                    f"Nama Pola Penipuan: {pattern.name}.\n"
                    f"Kategori: {pattern.category}.\n"
                    f"Deskripsi: {pattern.description}\n"
                    f"Kata kunci umum yang digunakan: {keyword_list}."
                )
                try:
                    vec = await embedding_svc.embed_text(embed_text)
                    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                    doc_id = f"pattern_{pattern.id}"
                    await db.execute_raw(
                        """
                        INSERT INTO rag_knowledge_base
                            (id, title, content, source, category, embedding, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6::vector, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW();
                        """,
                        doc_id,
                        pattern.name,
                        embed_text,
                        f"ScamPattern DB (riskWeight={pattern.riskWeight:.1f})",
                        pattern.category,
                        vec_str,
                    )
                    synced += 1
                except Exception as p_exc:
                    logger.warning("Failed to embed pattern '%s': %s", pattern.name, p_exc)

            logger.info(
                "✅ Synced %d/%d ScamPatterns to rag_knowledge_base",
                synced, len(patterns),
            )
            return synced
        except Exception as exc:
            logger.error("Error syncing scam patterns to knowledge base: %s", exc)
            return 0


vector_store = VectorStoreService()
