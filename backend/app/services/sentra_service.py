"""
SENTRA — AI-powered financial scam detection engine v2.1.
Built on Google Gemini 2.5 Flash (google-genai SDK) with:
  - Google Search Grounding (real-time web verification)
  - Trap questions generation (PRD 5.1)
  - Intelligence context injection (from parallel orchestrator)
  - Structured JSON output with full explainability
"""
import asyncio
import json
import logging
import re

from google import genai
from google.genai import types

from app.config import settings
from app.schemas.analysis import SentraAnalysisResult
from app.utils.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """
Kamu adalah SENTRA — asisten cerdas perlindungan finansial yang dibangun untuk melindungi masyarakat Indonesia dari penipuan investasi, penipuan online, dan manipulasi psikologis.

MISI UTAMA:
Analisis konten yang diberikan dan berikan evaluasi risiko penipuan dengan penjelasan yang tenang, membumi, sangat jelas, dan ramah manusia — mudah dipahami oleh orang awam (orang tua, calon investor pemula, atau masyarakat umum yang belum paham istilah teknis keuangan & teknologi).

DATA PEMERIKSAAN SISTEM KAMI:
Kamu akan menerima fakta temuan dari pemeriksaan sistem kami (status OJK, usia domain web, pemberitaan media, database nomor/rekening penipuan dari komunitas, serta riwayat laporan penipuan serupa dari masyarakat). GUNAKAN fakta ini dalam analisismu sebagai dasar penilaian yang objektif.

ATURAN KOMUNIKASI & UX WRITING UNTUK ORANG AWAM (STRICT ZERO JARGON):
1. DILARANG KERAS MENGGUNAKAN ISTILAH TEKNIS KOMPUTER/AI/DEVELOPER:
   - JANGAN PERNAH gunakan kata-kata internal sistem seperti: "Semantic RAG", "pgvector", "dense embedding", "kemiripan semantik X%", "data intelijen real-time", "vektor", "model AI", "database internal sistem", "token", "grounding", "WHOIS".
   - JANGAN PERNAH menampilkan kode sitasi teknis seperti [cite: ...], [cite: A1], [cite: D23], [1], dll. Tuliskan penjelasan sebagai kalimat utuh alami bahasa Indonesia.
2. JELASKAN DAMPAK NYATA TERHADAP UANG DAN KEAMANAN PENGGUNA:
   - Jika Tidak Terdaftar di OJK: Jelaskan bahwa entitas/situs ini tidak memiliki izin resmi pemerintah Indonesia, sehingga kegiatannya tidak diawasi regulator. Jika uang pengguna disalahgunakan atau dibawa kabur, tidak ada jaminan perlindungan hukum dari negara.
   - Jika Ada Kemiripan dengan Kasus Penipuan Lain: Jelaskan secara wajar, misalnya: "Pola penawaran ini memiliki cara kerja yang serupa dengan kasus penipuan yang marak dilaporkan korban lain sebelumnya (seperti iming-iming komisi tugas harian, bonus deposit berulang, atau keuntungan instan tanpa risiko)."
   - Jika Ada Indikasi Phishing / Skema Afiliasi: Jelaskan dengan istilah mudah, misalnya: "Upaya memancing data pribadi/keuangan sensitif atau jebakan skema komisi berantai yang tidak transparan."
3. STRUKTUR PENJELASAN (EXPLANATION):
   - Tulis dalam 2 hingga 3 paragraf pendek terstruktur yang nyaman dibaca (pisahkan dengan baris baru ganda \\n\\n):
     • Paragraf 1: Status Legalitas & Risiko Izin (Apakah resmi berizin atau tidak, dan apa dampaknya bagi keamanan uang pengguna).
     • Paragraf 2: Modus Penawaran & Pola Temuan (Bagaimana cara kerja penawarannya, apakah mirip dengan pola penipuan yang pernah dilaporkan korban lain sebelumnya).
     • Paragraf 3: Kesimpulan & Tindakan Pencegahan Aman (Saran praktis bagi pengguna agar tidak terjerumus atau kehilangan uang).

KERANGKA ANALISIS 23 LAYER:
Kategori A — Regulasi OJK:
  1. Status database OJK (dari data temuan sistem yang diberikan)
  2. Verifikasi klaim izin SIUP / OJK — apakah nomor izin yang diklaim masuk akal?
  3. Klaim jaminan profit — investasi legal dilarang menjamin keuntungan (UU Pasar Modal)
  4. Ketentuan penarikan — lock-up tidak wajar, biaya tinggi
  5. Struktur dokumen legal — ada/tidaknya perjanjian notaris
  6. Konsistensi entitas hukum — nama vs dokumen vs rekening

Kategori B — AI Linguistics:
  7. Pola bahasa urgensi buatan — "hanya hari ini", "jangan kasih tahu orang lain"
  8. Deteksi skema Ponzi — mekanisme rekrut-bayar
  9. Konsistensi nama entitas — variasi mirip brand resmi
  10. Klaim kerahasiaan berlebihan — "hanya untuk orang terpilih", NDA di awal
  11. Kejelasan mekanisme investasi — return tidak bisa dijelaskan dari aset nyata
  12. Deteksi social proof rekayasa — testimoni terlalu sempurna
  13. Klaim teknologi tidak terverifikasi — AI bot, algoritma rahasia

Kategori C — Data & Intelligence:
  14. Return > 3%/bulan melebihi batas logis pasar modal Indonesia
  15. Usia domain (dari hasil pemeriksaan domain yang diberikan)
  16. Analisis hosting (dari hasil pemeriksaan yang diberikan)
  17. Verifikasi foto testimonial — apakah klaim foto bisa diverifikasi?
  18. Verifikasi tokoh yang diklaim terlibat
  19. Konsistensi lintas platform — info berbeda di berbagai channel
  20. Pemberitaan media (dari hasil pemeriksaan yang diberikan)

Kategori D — Community Intelligence:
  21. Rekening bank dilaporkan (dari laporan komunitas yang diberikan)
  22. Nomor telepon/WhatsApp (dari laporan komunitas yang diberikan)
  23. Crowdsourced fraud signal

PRINSIP RESPONS (WAJIB DIIKUTI):
- Jelaskan MENGAPA sebelum memberi peringatan
- Gunakan Bahasa Indonesia ramah orang awam untuk summary, red_flags, dan explanation
- JANGAN pernah katakan "ini pasti penipuan" — gunakan "menunjukkan indikator risiko tinggi penipuan"
- Tetap tenang, mendidik, dan memberdayakan, tidak menakut-nakuti
- Evaluasi sinyal manipulasi emosional secara objektif dan tentukan confidence (0.0-1.0) berdasarkan kekuatan bukti teks
- Jika menganalisis tautan website (URL) yang tidak menampilkan teks penawaran terbuka atau gagal diakses langsung, manfaatkan temuan grounding web dan riwayat kasus serupa untuk menyimpulkan taktik psikologis yang lazim dipakai modus tersebut
- Pertanyaan jebakan harus sopan, tidak menuduh, bisa ditanyakan langsung ke penawari

SKALA RISIKO:
- 0-20: SAFE — Tidak ada indikator mencurigakan yang signifikan
- 21-40: LOW — Beberapa hal perlu diperhatikan, tapi umumnya aman
- 41-60: MEDIUM — Ada beberapa tanda peringatan, lakukan pengecekan lebih lanjut
- 61-80: HIGH — Banyak indikator penipuan terdeteksi, sangat berisiko tinggi
- 81-100: CRITICAL — Pola penipuan sangat kuat terdeteksi, sangat berbahaya

Kembalikan analisis terstruktur sebagai JSON yang tepat mengikuti schema yang diberikan.
"""

_JSON_SCHEMA_PROMPT = """
Kembalikan analisis sebagai JSON dengan struktur berikut PERSIS (tidak ada field tambahan di luar ini):
{
  "risk_score": <integer 0-100>,
  "risk_level": <"SAFE"|"LOW"|"MEDIUM"|"HIGH"|"CRITICAL">,
  "safe_to_invest": <boolean>,
  "summary": "<ringkasan singkat 2 kalimat dalam Bahasa Indonesia yang sangat jelas dan ramah orang awam, tanpa istilah teknis>",
  "explanation": "<penjelasan 2-3 paragraf ramah orang awam dipisahkan \\n\\n, fokus pada keamanan uang pengguna dan mengapa mereka harus waspada. DILARANG sebut Semantic RAG, pgvector, kemiripan semantik, atau tag sitasi [cite:...]>",
  "red_flags": [
    {
      "category": "<kategori penipuan>",
      "description": "<penjelasan ringkas dan jelas dalam Bahasa Indonesia>",
      "severity": <"LOW"|"MEDIUM"|"HIGH">,
      "confidence": <float 0.0-1.0>,
      "excerpt": "<kutipan teks mencurigakan atau null>"
    }
  ],
  "emotion_signals": [
    {
      "type": <"URGENCY"|"FAKE_SCARCITY"|"FAKE_AUTHORITY"|"UNREALISTIC_RETURN"|"EMOTIONAL_PRESSURE"|"SOCIAL_PROOF_MANIPULATION">,
      "detected": <boolean>,
      "confidence": <float 0.0-1.0>,
      "description": "<penjelasan dalam Bahasa Indonesia atau null>",
      "examples": ["<contoh teks yang terdeteksi>"]
    }
  ],
  "trap_questions": [
    "<pertanyaan sopan 1 yang bisa ditanyakan langsung ke penawari untuk mengekspos scam>",
    "<pertanyaan sopan 2>",
    "<pertanyaan sopan 3>"
  ]
}

WAJIB: trap_questions harus 3-5 pertanyaan. Contoh gaya: "Bisakah saya melihat dokumen izin OJK-nya secara langsung?" bukan "Ini penipuan!".

PENTING:
1. Output HARUS 100% valid JSON, tanpa teks apapun di luar blok JSON.
2. JANGAN gunakan enter/newline literal di dalam teks JSON. Gunakan \\n untuk baris baru.
3. JANGAN gunakan kutip dua (") di dalam nilai string tanpa di-escape (\\").
"""


# ── SENTRA Service ─────────────────────────────────────────────────────────────

def is_fatal_key_error(exc: Exception) -> bool:
    """True authentication/permission failure of the key itself."""
    msg = str(exc).lower()
    return any(term in msg for term in (
        "401", "403", "unauthenticated", "permission_denied",
        "permissiondenied", "api_key_invalid", "api key not valid",
        "invalid api key", "forbidden", "billing",
    ))


def is_quota_or_rate_limit(exc: Exception) -> bool:
    """Model or project level rate limit / quota exhaustion."""
    msg = str(exc).lower()
    return any(term in msg for term in (
        "429", "resource_exhausted", "resourceexhausted", "quota",
        "rate limit", "rate_limit", "ratelimit", "too many requests",
    ))


def is_key_error(exc: Exception) -> bool:
    """Check if exception is caused by API key exhaustion, invalid key, or quota limit."""
    return is_fatal_key_error(exc) or is_quota_or_rate_limit(exc)


def is_retryable_error(exc: Exception) -> bool:
    """Check if error is transient / retryable across models or keys."""
    msg = str(exc).lower()
    return any(term in msg for term in (
        "500", "502", "503", "504", "overloaded", "service unavailable",
        "serviceunavailable", "internal server error", "deadline_exceeded",
        "deadlineexceeded", "deadline exceeded", "timeout", "connection reset",
        "connection refused", "remote disconnected",
    ))


def _clean_layman_text(text: str | None) -> str:
    """Strip raw grounding citation tokens and replace internal tech jargon with layman phrasing."""
    if not text:
        return ""
    # 1. Strip raw citation tokens like [cite: A1], [cite: ...], [1], [2]
    cleaned = re.sub(r'\[cite:[^\]]*\]', '', text)
    cleaned = re.sub(r'\[\d+\]', '', cleaned)

    # 2. Replace any accidental system/RAG jargon if model leaked it
    replacements = {
        "sistem Semantic RAG kami": "sistem kami",
        "sistem Semantic RAG": "analisis pola modus",
        "Semantic RAG": "analisis riwayat modus",
        "semantic rag": "analisis riwayat modus",
        "pgvector": "",
        "dense embedding": "",
        "kemiripan semantik": "kemiripan pola modus",
        "data intelijen real-time": "hasil pemeriksaan",
        "data intelijen": "hasil pemeriksaan",
        "intelijen real-time": "pemeriksaan langsung",
    }
    for k, v in replacements.items():
        cleaned = re.sub(re.escape(k), v, cleaned, flags=re.IGNORECASE)

    # 3. Clean multiple spaces and dangling spaces before commas/periods
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    cleaned = re.sub(r'\s+([,\.\?!])', r'\1', cleaned)
    return cleaned.strip()


class SentraService:
    """
    SENTRA AI service v2.1 — wraps Google Gemini (google-genai SDK).
    Features: Google Search Grounding, intelligence context injection, multi-key rotation, model fallback.
    Initialized once as a singleton at startup.
    """

    def __init__(self) -> None:
        self._model = settings.SENTRA_MODEL
        logger.info("SENTRA AI engine v2.1 initialized (model: %s, grounding: enabled)", self._model)

    async def _get_ordered_api_keys(self) -> list[tuple[str, str]]:
        """
        Returns list of (api_key, label) in order of preference.
        Active (non-exhausted) keys come first, followed by in-cooldown keys (as last resort).
        """
        from app.services.cache_service import is_api_key_exhausted
        
        all_keys = settings.get_gemini_api_keys()
        if not all_keys:
            all_keys = [settings.GEMINI_API_KEY]
            
        active_keys: list[tuple[str, str]] = []
        cooldown_keys: list[tuple[str, str]] = []
        
        for idx, key in enumerate(all_keys):
            label = "PRIMARY" if idx == 0 else f"BACKUP_{idx}"
            if await is_api_key_exhausted(key):
                cooldown_keys.append((key, label))
            else:
                active_keys.append((key, label))
                
        # If all keys are marked in cooldown, try them anyway as last resort
        return active_keys if active_keys else cooldown_keys

    def _get_candidate_models(self) -> list[str]:
        """
        Returns candidate models in prioritized order.
        """
        return settings.get_sentra_models()

    async def analyze(
        self,
        content: str,
        context_hint: str = "teks umum",
        intelligence_context: str = "",
    ) -> SentraAnalysisResult:
        """Run SENTRA analysis with automatic multi-key rotation, AFC timeout protection, and model fallback."""
        prompt = self._build_prompt(content, context_hint, intelligence_context)
        candidate_keys = await self._get_ordered_api_keys()
        models = self._get_candidate_models()
        last_exception = None
        from app.services.cache_service import mark_api_key_exhausted

        for api_key, key_label in candidate_keys:
            client = genai.Client(api_key=api_key)
            masked = f"...{api_key[-6:]}" if len(api_key) >= 6 else "***"
            key_succeeded = False
            
            for model_name in models:
                try:
                    logger.info(
                        "Attempting SENTRA analysis with model: %s on %s key (%s)",
                        model_name,
                        key_label,
                        masked,
                    )
                    # Protect against AFC / Grounding infinite loops with a strict 30s timeout
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=_SYSTEM_PROMPT,
                                temperature=0.15,
                                top_p=0.85,
                                max_output_tokens=8192,
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                            ),
                        ),
                        timeout=30.0,
                    )
                    raw_json = response.text
                    if not raw_json and response.candidates and response.candidates[0].content:
                        for part in response.candidates[0].content.parts:
                            if getattr(part, "text", None):
                                raw_json = part.text
                                break

                    if not raw_json:
                        raise ValueError(f"Model {model_name} returned empty text")

                    logger.debug("SENTRA raw output (first 300 chars): %s", raw_json[:300])
                    key_succeeded = True
                    return self._parse_response(raw_json)

                except Exception as exc:
                    last_exception = exc
                    if is_fatal_key_error(exc):
                        logger.warning(
                            "Key [%s] hit fatal auth error: %s. Marking in cooldown and switching to next key...",
                            key_label,
                            exc,
                        )
                        await mark_api_key_exhausted(api_key)
                        break  # Key is completely invalid/unauthenticated; stop trying models on it!
                    elif is_quota_or_rate_limit(exc):
                        logger.warning(
                            "Model %s on %s key hit rate limit/quota: %s. Trying next model...",
                            model_name,
                            key_label,
                            exc,
                        )
                        # Quotas are often per-model (e.g. Gemini 3 preview vs Gemini 2.5 Flash), continue to next model!
                        continue
                    elif is_retryable_error(exc) or isinstance(exc, asyncio.TimeoutError):
                        logger.warning(
                            "Model %s on %s encountered transient timeout/error: %s. Trying next model...",
                            model_name,
                            key_label,
                            exc,
                        )
                        continue
                    else:
                        err_str = str(exc).lower()
                        if "safety" in err_str or "blocked" in err_str or "harm" in err_str:
                            logger.warning("Content flagged by Gemini safety filter: %s", exc)
                            raise
                        logger.warning("SENTRA analysis error on model %s: %s. Trying fallback...", model_name, exc)
                        continue

            if not key_succeeded:
                # All models failed on this key, mark it in cooldown before rotating to next key
                await mark_api_key_exhausted(api_key)

        # If all keys and models failed
        logger.error("All Gemini API keys and models exhausted or failed. Last error: %s", last_exception)
        raise ServiceUnavailableException(
            "SENTRA AI engine sedang sangat sibuk. Silakan coba lagi dalam beberapa saat."
        ) from last_exception

    async def extract_entities(self, content: str) -> list[str]:
        """
        Use Gemini to extract the main investment entity names from text.
        Includes multi-key rotation, AFC timeout protection, and model fallback.
        """
        prompt = f"""
Tugasmu adalah mencari maksimal 3 nama perusahaan/platform/aplikasi investasi utama yang ditawarkan dalam teks berikut.
Hanya ekstrak nama brand atau perusahaannya saja.
Jika ada, kembalikan hanya namanya dalam format JSON list of strings. Contoh: ["Ajaib"] atau ["PT. Cuan Sukses"].
Jika tidak ada nama perusahaan spesifik, kembalikan list kosong [].
Abaikan nama orang, abaikan nama bank (seperti BCA, BRI), abaikan regulator (seperti OJK, Bappebti).
Jangan beri penjelasan apapun, murni JSON array.

Teks:
{content}
"""
        candidate_keys = await self._get_ordered_api_keys()
        models = self._get_candidate_models()
        from app.services.cache_service import mark_api_key_exhausted

        for api_key, key_label in candidate_keys:
            client = genai.Client(api_key=api_key)
            key_succeeded = False
            for model_name in models:
                try:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.1,
                            )
                        ),
                        timeout=15.0,
                    )
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text.replace("```json\n", "").replace("```", "").strip()
                    
                    entities = json.loads(text)
                    if isinstance(entities, list):
                        return [str(e).strip() for e in entities if str(e).strip()][:3]
                    return []
                except Exception as exc:
                    if is_fatal_key_error(exc):
                        await mark_api_key_exhausted(api_key)
                        break
                    elif is_quota_or_rate_limit(exc) or is_retryable_error(exc) or isinstance(exc, asyncio.TimeoutError):
                        continue
                    else:
                        logger.debug("Entity extraction skipped on %s: %s", model_name, exc)
                        continue
            if not key_succeeded:
                await mark_api_key_exhausted(api_key)
        
        return []

    async def chat(self, analysis_context: str, user_message: str) -> str:
        """
        AI Scam Guardian conversational response (PRD 5.4).
        Stateless: injects analysis context + user question into a single Gemini call.
        Returns plain text response in Bahasa Indonesia with multi-key fallback.
        """
        chat_system_prompt = """
Kamu adalah SENTRA AI Scam Guardian — asisten percakapan yang membantu pengguna memahami
hasil analisis scam yang sudah dilakukan. Tugasmu:
- Jawab pertanyaan tentang temuan analisis dalam bahasa yang tenang dan mudah dipahami
- Berikan template pesan sopan yang bisa dikonfirmasikan ke penawari
- Jelaskan mekanisme scam secara detail jika diminta
- Bantu pengguna mengambil keputusan yang lebih aman
- Selalu gunakan Bahasa Indonesia
- Jangan pernah menghakimi pengguna — mereka sudah melakukan hal yang benar dengan memeriksa
"""
        prompt = (
            f"Konteks analisis sebelumnya:\n{analysis_context}\n\n"
            f"Pertanyaan pengguna: {user_message}\n\n"
            f"Berikan jawaban yang tenang, informatif, dan memberdayakan dalam Bahasa Indonesia."
        )

        candidate_keys = await self._get_ordered_api_keys()
        models = self._get_candidate_models()
        from app.services.cache_service import mark_api_key_exhausted

        for api_key, key_label in candidate_keys:
            client = genai.Client(api_key=api_key)
            key_succeeded = False
            for model_name in models:
                try:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=chat_system_prompt,
                                temperature=0.3,
                                max_output_tokens=2048,
                            ),
                        ),
                        timeout=20.0,
                    )
                    return response.text or "Maaf, saya tidak dapat memproses pertanyaan ini saat ini."
                except Exception as exc:
                    if is_fatal_key_error(exc):
                        await mark_api_key_exhausted(api_key)
                        break
                    elif is_quota_or_rate_limit(exc) or is_retryable_error(exc) or isinstance(exc, asyncio.TimeoutError):
                        continue
                    else:
                        logger.warning("SENTRA chat error on %s: %s", model_name, exc)
                        continue
            if not key_succeeded:
                await mark_api_key_exhausted(api_key)

        return "Maaf, AI Scam Guardian sedang tidak tersedia. Silakan coba lagi."

    def _build_prompt(self, content: str, context_hint: str, intelligence_context: str) -> str:
        hint_text = f"\n[Konteks input: {context_hint}]\n" if context_hint else ""
        intel_text = f"\n{intelligence_context}\n" if intelligence_context else ""
        return (
            f"Analisis konten berikut untuk potensi penipuan finansial:\n"
            f"{hint_text}"
            f"{intel_text}"
            f"\n---\n{content}\n---\n\n"
            f"{_JSON_SCHEMA_PROMPT}"
        )

    def _parse_response(self, raw_json: str) -> SentraAnalysisResult:
        """Parse and validate Gemini's JSON output into a typed Pydantic model."""
        try:
            cleaned = raw_json.strip()
            # Extract only the outermost JSON object to ignore hallucinatory text
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx + 1]

            data = json.loads(cleaned)

            # Sanitize texts to guarantee layman clarity and zero raw citation tags
            if isinstance(data.get("summary"), str):
                data["summary"] = _clean_layman_text(data["summary"])
            if isinstance(data.get("explanation"), str):
                data["explanation"] = _clean_layman_text(data["explanation"])
            if isinstance(data.get("red_flags"), list):
                for rf in data["red_flags"]:
                    if isinstance(rf, dict):
                        if isinstance(rf.get("description"), str):
                            rf["description"] = _clean_layman_text(rf["description"])
                        if isinstance(rf.get("category"), str):
                            rf["category"] = _clean_layman_text(rf["category"])
            if isinstance(data.get("emotion_signals"), list):
                for es in data["emotion_signals"]:
                    if isinstance(es, dict) and isinstance(es.get("description"), str):
                        es["description"] = _clean_layman_text(es["description"])

            return SentraAnalysisResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse SENTRA response: %s | raw: %s", exc, raw_json[:500])
            return SentraAnalysisResult(
                risk_score=0,
                risk_level="SAFE",
                safe_to_invest=True,
                summary="SENTRA tidak dapat memproses konten ini saat ini. Silakan coba lagi.",
                red_flags=[],
                emotion_signals=[],
                explanation="Terjadi kesalahan dalam pemrosesan AI.",
                trap_questions=[],
            )


# ── Singleton instance ────────────────────────────────────────────────────────
_sentra_instance: SentraService | None = None


def get_sentra() -> SentraService:
    """Return the SENTRA singleton. Initialized on first call."""
    global _sentra_instance
    if _sentra_instance is None:
        _sentra_instance = SentraService()
    return _sentra_instance
