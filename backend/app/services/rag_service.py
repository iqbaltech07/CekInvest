"""
Dense Semantic RAG (Retrieval-Augmented Generation) Service.
Combines Google Gemini embeddings (gemini-embedding-001) with PostgreSQL pgvector
to retrieve semantically similar historical cases and authoritative OJK regulations.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional
from prisma import Prisma

from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

@dataclass
class RAGResult:
    similar_reports: list[dict[str, Any]] = field(default_factory=list)
    regulatory_articles: list[dict[str, Any]] = field(default_factory=list)
    top_similarity: float = 0.0
    matched_scam_count: int = 0
    matched_legit_count: int = 0

    def to_prompt_context(self) -> str:
        """Format retrieved semantic knowledge into a structured prompt block for SENTRA AI."""
        if not self.similar_reports and not self.regulatory_articles:
            return ""

        sections = []

        # 1. Similar Historical Cases
        if self.similar_reports:
            sections.append("\n=== [RIWAYAT LAPORAN MODUS PENIPUAN SERUPA DARI KORBAN LAIN] ===")
            sections.append(
                "Catatan riwayat laporan penipuan dengan modus atau penawaran serupa di masa lalu "
                "(PENTING: Jelaskan kepada pengguna dengan bahasa manusia yang sederhana bahwa pola penawaran ini "
                "identik dengan modus penipuan yang marak dilaporkan korban lain. Jangan gunakan istilah teknologi atau sistem):"
            )
            for idx, item in enumerate(self.similar_reports, 1):
                status_label = "⚠️ TERINDIKASI PENIPUAN (SCAM)" if item["is_scam"] else "✓ TERVERIFIKASI LEGAL"
                sim_pct = int(item["similarity"] * 100)
                excerpt = item["raw_input"][:180].replace("\n", " ")
                sections.append(
                    f"{idx}. [{status_label}] Kategori Modus: {item['category']} (Tingkat Kemiripan Modus: {sim_pct}%)\n"
                    f"   Cuplikan Kasus Serupa: \"{excerpt}...\""
                )

        # 2. Authoritative OJK & Legal Articles
        if self.regulatory_articles:
            sections.append("\n=== [KETENTUAN REGULATOR RESMI (OJK / BAPPEBTI)] ===")
            sections.append(
                "Gunakan ketentuan resmi berikut untuk menjelaskan alasan hukum dan risiko keuangan kepada pengguna "
                "dengan bahasa yang mudah dipahami orang awam:"
            )
            for item in self.regulatory_articles:
                sim_pct = int(item["similarity"] * 100)
                sections.append(
                    f"• {item['title']} (Sumber Aturan: {item['source']}, Tingkat Relevansi: {sim_pct}%)\n"
                    f"  Isi Ketentuan: {item['content']}"
                )

        return "\n".join(sections)


class RAGService:
    """Orchestrates embedding generation, vector search, and context assembly."""

    def __init__(self) -> None:
        self.embedding_svc = embedding_service
        self.vector_store = vector_store

    async def query_rag(
        self,
        text: str,
        db: Prisma,
        report_limit: int = 3,
        article_limit: int = 2,
    ) -> RAGResult:
        """
        Executes dense semantic retrieval for the input text using gemini-embedding-001
        and pgvector cosine similarity search.
        """
        try:
            # 1. Generate 768-dim dense embedding
            query_vec = await self.embedding_svc.embed_text(text)

            # 2. Search similar reports
            similar_reports = await self.vector_store.search_similar_reports(
                db=db,
                query_embedding=query_vec,
                limit=report_limit,
                min_similarity=0.48,
            )

            # 3. Search authoritative OJK knowledge base
            regulatory_articles = await self.vector_store.search_knowledge_base(
                db=db,
                query_embedding=query_vec,
                limit=article_limit,
                min_similarity=0.42,
            )

            top_sim = max([r["similarity"] for r in similar_reports], default=0.0)
            scam_count = sum(1 for r in similar_reports if r["is_scam"])
            legit_count = sum(1 for r in similar_reports if not r["is_scam"])

            logger.info(
                "RAG Retrieval complete: %d similar reports (top=%.2f), %d regulatory articles",
                len(similar_reports), top_sim, len(regulatory_articles)
            )

            return RAGResult(
                similar_reports=similar_reports,
                regulatory_articles=regulatory_articles,
                top_similarity=top_sim,
                matched_scam_count=scam_count,
                matched_legit_count=legit_count,
            )

        except Exception as exc:
            logger.warning("RAG retrieval failed gracefully: %s", exc)
            return RAGResult()

    async def sync_all_reports_to_vector_store(self, db: Prisma) -> int:
        """
        Scans all UserReports in the database and computes dense gemini-embedding-001 vectors,
        populating the report_embeddings pgvector table.
        Also syncs ScamPattern records to rag_knowledge_base for semantic pattern retrieval.
        """
        try:
            await self.vector_store.init_vector_tables(db)
            await self.vector_store.seed_knowledge_base_if_empty(db, self.embedding_svc)

            # Sync ScamPatterns as semantic embeddings (replaces keyword matching)
            pattern_count = await self.vector_store.sync_scam_patterns_to_knowledge_base(
                db, self.embedding_svc
            )
            logger.info("Pattern sync: %d patterns embedded into rag_knowledge_base", pattern_count)

            reports = await db.userreport.find_many()
            if not reports:
                return 0

            logger.info("Syncing %d UserReports to pgvector store with gemini-embedding-001...", len(reports))
            synced = 0
            for r in reports:
                if not r.rawInput or len(r.rawInput.strip()) < 5:
                    continue
                try:
                    vec = await self.embedding_svc.embed_text(r.rawInput)
                    await self.vector_store.upsert_report_embedding(
                        db=db,
                        report_id=r.id,
                        raw_input=r.rawInput,
                        is_scam=r.isScam,
                        scam_category=r.scamCategory,
                        embedding=vec,
                    )
                    synced += 1
                except Exception as rec_exc:
                    logger.warning("Failed to embed report %s: %s", r.id, rec_exc)

            logger.info("✅ Successfully synced %d user reports to report_embeddings", synced)
            return synced

        except Exception as exc:
            logger.error("Error syncing reports to vector store: %s", exc)
            raise exc



# Global singleton instance
rag_service = RAGService()
