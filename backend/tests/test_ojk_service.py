import pytest
import pytest_asyncio
from prisma import Prisma

from app.services.ojk_service import (
    check_entity,
    is_valid_entity_candidate,
    OjkCheckResult,
    _registry_engine
)
from app.services.intelligence_orchestrator import _extract_entity_names


@pytest.mark.asyncio
async def test_ojk_licensed_entities(db: Prisma):
    """Test that legitimate financial entities are correctly identified as TERDAFTAR."""
    test_cases = [
        ("Bibit", "TERDAFTAR"),
        ("PT Bibit Tumbuh Bersama", "TERDAFTAR"),
        ("PT Stockbit Sekuritas Digital", "TERDAFTAR"),
        ("Stockbit", "TERDAFTAR"),
        ("J.P. Morgan", "TERDAFTAR"),
        ("PT J.P. Morgan Sekuritas Indonesia", "TERDAFTAR"),
        ("PT Semesta Indovest Sekuritas", "TERDAFTAR"),
        ("Semesta Indovest", "TERDAFTAR"),
        ("PT UBS Sekuritas Indonesia", "TERDAFTAR"),
        ("Manulife", "TERDAFTAR"),
        ("Bareksa", "TERDAFTAR"),
        ("Tokocrypto", "TERDAFTAR"),
        ("Tanamduit", "TERDAFTAR"),
    ]

    for name, expected_status in test_cases:
        res = await check_entity(name, db)
        assert res.status == expected_status, f"Failed for {name}: got {res.status}, expected {expected_status}"
        assert res.source_url is not None


@pytest.mark.asyncio
async def test_ojk_illegal_entities(db: Prisma):
    """Test that known illegal entities are correctly flagged as TERINDIKASI_ILEGAL."""
    test_cases = [
        "AMADEUS GADAI",
        "Robocash - Online Loan Robot",
    ]

    for name in test_cases:
        res = await check_entity(name, db)
        assert res.status == "TERINDIKASI_ILEGAL", f"Failed for {name}: got {res.status}"
        assert "ilegal" in res.detail.lower() or "diblokir" in res.detail.lower()


@pytest.mark.asyncio
async def test_ojk_reject_junk_and_common_words(db: Prisma):
    """
    CRITICAL TEST: Ensure common chat words and generic terms
    are NEVER identified as TERDAFTAR and never hallucinate.
    """
    junk_words = [
        "robot",
        "slot",
        "keuntungan",
        "gila sih",
        "url",
        "deposit",
        "mba skip",
        "selamat",
        "konten",
        "bergabunglah",
        "sekuritas",
        "investasi",
    ]

    for word in junk_words:
        assert not is_valid_entity_candidate(word) or word in ["sekuritas", "investasi"]
        res = await check_entity(word, db)
        assert res.status == "TIDAK_DITEMUKAN", f"Junk word '{word}' must be TIDAK_DITEMUKAN, got {res.status}"
        assert res.source_url is None, f"Junk word '{word}' should not have source_url, got {res.source_url}"


def test_contextual_entity_extraction():
    """Test that heuristic entity extraction only catches real company candidates and ignores conversational words."""
    chat_text_with_pt = "Halo mas, segera daftar di PT Semesta Indovest Sekuritas atau aplikasi Ajaib untuk dapat bonus."
    entities = _extract_entity_names(chat_text_with_pt)
    assert any("Semesta Indovest" in e for e in entities)

    chat_text_scam_no_entity = "Selamat pagi kak, kami ada robot trading otomatis cuan gila sih. Deposit 500rb per hari langsung untung slot gacor."
    entities_scam = _extract_entity_names(chat_text_scam_no_entity)
    # Must NOT extract 'Selamat', 'Robot', 'Deposit', 'Cuan', 'Slot', 'Gila'
    assert "Selamat" not in entities_scam
    assert "Robot" not in entities_scam
    assert "Deposit" not in entities_scam
    assert "Slot" not in entities_scam
    assert len(entities_scam) == 0
