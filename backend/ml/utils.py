"""
Utility functions for graph construction and feature engineering.
ML dependencies (numpy, sklearn) are lazily imported to avoid crashes
when these packages are not installed.
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Text Processing ────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove extra whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def compute_tfidf_features(texts: list[str], max_features: int = 64):
    """
    Compute TF-IDF features for a list of texts.
    Returns a numpy array of shape (n_texts, max_features).
    Lazy-imports sklearn on first call.
    """
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not texts:
        return np.zeros((0, max_features))

    normalized = [normalize_text(t) for t in texts]
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=1,
        ngram_range=(1, 2),
        stop_words=None,
    )
    try:
        features = vectorizer.fit_transform(normalized).toarray()
        return features
    except Exception as exc:
        logger.warning("TF-IDF computation failed: %s", exc)
        return np.zeros((len(texts), max_features))

def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute cosine similarity between two texts using TF-IDF.
    Returns float in [0, 1].
    """
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    try:
        texts = [normalize_text(text1), normalize_text(text2)]
        vec = TfidfVectorizer(min_df=1, ngram_range=(1, 2)).fit_transform(texts)
        sim = cosine_similarity(vec[0:1], vec[1:2])[0][0]
        return float(sim)
    except Exception:
        return 0.0

# ── Entity Extraction ──────────────────────────────────────────────────────

def extract_phone_numbers(text: str) -> list[str]:
    """Extract normalized Indonesian phone numbers from text."""
    pattern = r"(?:0|\+62|62)[\s\-]?(?:8[1-9]|21|22|31)[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{0,4}"
    raw = re.findall(pattern, text)
    phones = []
    for p in raw:
        digits = re.sub(r"\D", "", p)
        if digits.startswith("62"):
            digits = "0" + digits[2:]
        if 9 <= len(digits) <= 13:
            phones.append(digits)
    return list(set(phones))

def extract_bank_accounts(text: str) -> list[tuple[str, str]]:
    """Extract (bank_name, account_number) pairs from text."""
    bank_names = [
        "BCA", "BRI", "BNI", "Mandiri", "BSI", "CIMB", "Danamon",
        "Permata", "BTN", "OCBC", "Maybank", "BRK", "Jago", "Jenius",
    ]
    results = []
    for bank in bank_names:
        pattern = rf"(?:{bank}|{bank.lower()})[^\d]{{0,20}}(\d{{8,16}})"
        matches = re.findall(pattern, text, re.IGNORECASE)
        for acct in matches:
            results.append((bank, acct))
    return results[:5]

def extract_domains(text: str) -> list[str]:
    """Extract domains/URLs from text."""
    pattern = r"(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    domains = []
    for match in matches:
        if isinstance(match, tuple):
            match = match[0]
        domain = match.strip().lower()
        if domain and not domain.startswith("www."):
            domains.append(domain)
    return list(set(domains))[:5]

# ── Feature Engineering ────────────────────────────────────────────────────

def compute_account_features(report_count: int, last_seen: datetime | None):
    """
    Compute features for BankAccount/Phone/Domain nodes.
    Returns 8-dimensional numpy array.
    """
    import numpy as np

    features = np.zeros(8)
    features[0] = min(report_count / 100.0, 1.0)

    if last_seen:
        days_ago = (datetime.now(timezone.utc) - last_seen).days
        features[1] = min(days_ago / 365.0, 1.0)
    else:
        features[1] = 0.0

    features[2] = 1.0 if report_count > 10 else 0.0
    features[3] = 1.0 if report_count > 50 else 0.0

    return features

def compute_report_features(text: str, category: str | None, tfidf_vec):
    """
    Compute features for Report nodes.
    Combines TF-IDF (64-dim) with categorical encoding.
    Returns 64-dimensional numpy array.
    """
    import numpy as np

    features = np.zeros(64)

    if tfidf_vec is not None and len(tfidf_vec) > 0:
        features[:min(60, len(tfidf_vec))] = tfidf_vec[:60]

    categories = ["Robot Trading Scam", "Crypto Scam", "Investasi Bodong", "Ponzi"]
    if category in categories:
        idx = categories.index(category)
        features[60 + idx] = 1.0

    return features

# ── Graph Construction Helpers ─────────────────────────────────────────────

def hash_entity(entity_type: str, entity_value: str) -> str:
    """Generate deterministic hash ID for entities."""
    combined = f"{entity_type}:{entity_value}".lower()
    return hashlib.md5(combined.encode()).hexdigest()[:16]

def build_edge_index(edges: list[tuple[int, int]]):
    """
    Convert edge list to PyG edge_index format (2, num_edges).
    Returns numpy array.
    """
    import numpy as np

    if not edges:
        return np.zeros((2, 0), dtype=np.int64)
    edges_array = np.array(edges, dtype=np.int64).T
    return edges_array
