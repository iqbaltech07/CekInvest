"""
Tests for Human-Centric & Layman Copy Sanitization.
Ensures zero technical machine jargon leaks to end users and raw citation tags are cleaned.
"""
import pytest
from app.services.sentra_service import _clean_layman_text
from app.services.rag_service import RAGResult
from app.services.intelligence_orchestrator import IntelligenceCheckResult


def test_clean_layman_text_strips_citations():
    raw = (
        "Berdasarkan data intelijen real-time, situs https://mba1995.com tidak ditemukan "
        "dalam database OJK. [cite: A1] Yang lebih mengkhawatirkan, sistem Semantic RAG kami "
        "secara konsisten mengidentifikasi URL ini sebagai 'TERKONFIRMASI SCAM' dengan "
        "kemiripan semantik 87%. [cite: D23] Selain itu, ada risiko phishing finansial. [1] [cite: Dasar Hukum]"
    )
    cleaned = _clean_layman_text(raw)
    
    # Assert no citation tags remain
    assert "[cite:" not in cleaned
    assert "[1]" not in cleaned
    assert "[cite: A1]" not in cleaned
    assert "[cite: D23]" not in cleaned
    
    # Assert no internal RAG tech jargon remains
    assert "Semantic RAG" not in cleaned
    assert "kemiripan semantik" not in cleaned
    assert "data intelijen real-time" not in cleaned


def test_rag_result_to_prompt_context_has_no_raw_engineer_jargon():
    rag = RAGResult(
        similar_reports=[
            {
                "is_scam": True,
                "category": "Phishing Finansial",
                "similarity": 0.87,
                "raw_input": "Tawaran komisi harian deposit berulang",
            }
        ],
        regulatory_articles=[
            {
                "title": "Ketentuan Izin Pasar Modal",
                "source": "UU Pasar Modal",
                "similarity": 0.90,
                "content": "Setiap penawaran investasi wajib memiliki izin regulator.",
            }
        ],
    )
    context = rag.to_prompt_context()

    # Engineer headers replaced
    assert "SEMANTIC RAG PGVECTOR" not in context
    assert "dense embedding" not in context
    assert "gemini-embedding-001" not in context

    # Human-centric terms used
    assert "RIWAYAT LAPORAN MODUS PENIPUAN SERUPA" in context
    assert "Tingkat Kemiripan Modus" in context
    assert "KETENTUAN REGULATOR RESMI" in context


def test_orchestrator_prompt_context_has_humanized_header():
    intel = IntelligenceCheckResult(
        ojk_status="TIDAK_DITEMUKAN",
        domain="mba1995.com",
    )
    context = intel.to_prompt_context()

    assert "DATA INTELIJEN REAL-TIME" not in context
    assert "HASIL PEMERIKSAAN SISTEM CEKINVEST" in context
