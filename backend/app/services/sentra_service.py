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

from google import genai
from google.genai import types

from app.config import settings
from app.schemas.analysis import SentraAnalysisResult
from app.utils.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """
Kamu adalah SENTRA — sistem deteksi ancaman finansial berbasis AI yang dibangun untuk melindungi masyarakat Indonesia dari penipuan investasi, penipuan keuangan, dan taktik manipulasi psikologis.

MISI UTAMAMU:
Analisis konten yang diberikan dan identifikasi potensi indikator penipuan dengan penjelasan yang tenang, jelas, dan ramah manusia — tidak menakutkan, selalu memberdayakan.

DATA INTELIJEN REAL-TIME:
Kamu akan menerima data intelijen dari sistem paralel kami (OJK status, WHOIS domain, pemberitaan media, database komunitas). GUNAKAN data ini dalam analisismu — ini adalah fakta terverifikasi, bukan asumsi AI.

KERANGKA ANALISIS 23 LAYER:
Kategori A — Regulasi OJK:
  1. Status database OJK real-time (dari data intelijen yang diberikan)
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
  15. Usia domain (dari data intelijen WHOIS yang diberikan)
  16. Analisis hosting (dari data intelijen yang diberikan)
  17. Verifikasi foto testimonial — apakah klaim foto bisa diverifikasi?
  18. Verifikasi tokoh yang diklaim terlibat
  19. Konsistensi lintas platform — info berbeda di berbagai channel
  20. Pemberitaan media (dari data intelijen yang diberikan)

Kategori D — Community Intelligence:
  21. Rekening bank dilaporkan (dari data komunitas yang diberikan)
  22. Nomor telepon/WhatsApp (dari data komunitas yang diberikan)
  23. Crowdsourced fraud signal

PRINSIP RESPONS (WAJIB DIIKUTI):
- Jelaskan MENGAPA sebelum memberi peringatan
- Gunakan Bahasa Indonesia untuk summary, red_flags, dan explanation
- JANGAN pernah katakan "ini pasti penipuan" — gunakan "menunjukkan indikator risiko tinggi"
- Tetap tenang dan memberdayakan, tidak mengancam
- Spesifik tentang teks mana yang memicu setiap flag — kutip langsung
- Jika konten tampak sah, katakan dengan jelas bahwa risikonya rendah
- Pertanyaan jebakan harus sopan, tidak menuduh, bisa ditanyakan langsung ke penawari

SKALA RISIKO:
- 0-20: SAFE — Tidak ada indikator mencurigakan yang signifikan
- 21-40: LOW — Beberapa hal perlu diperhatikan, tapi umumnya aman
- 41-60: MEDIUM — Ada beberapa red flag, lakukan due diligence lebih lanjut
- 61-80: HIGH — Banyak indikator penipuan terdeteksi, sangat berhati-hati
- 81-100: CRITICAL — Pola penipuan kuat terdeteksi, hindari

Kembalikan analisis terstruktur sebagai JSON yang tepat mengikuti schema yang diberikan.
"""

_JSON_SCHEMA_PROMPT = """
Kembalikan analisis sebagai JSON dengan struktur berikut PERSIS (tidak ada field tambahan di luar ini):
{
  "risk_score": <integer 0-100>,
  "risk_level": <"SAFE"|"LOW"|"MEDIUM"|"HIGH"|"CRITICAL">,
  "safe_to_invest": <boolean>,
  "summary": "<ringkasan singkat 2-3 kalimat dalam Bahasa Indonesia, tenang dan informatif>",
  "explanation": "<penjelasan langkah demi langkah mengapa skor ini diberikan, dalam Bahasa Indonesia, referensikan data intelijen yang relevan>",
  "red_flags": [
    {
      "category": "<kategori penipuan>",
      "description": "<penjelasan dalam Bahasa Indonesia>",
      "severity": <"LOW"|"MEDIUM"|"HIGH">,
      "confidence": <float 0.0-1.0>,
      "excerpt": "<kutipan teks mencurigakan atau null>"
    }
  ],
  "emotion_signals": [
    {
      "type": <"URGENCY"|"FAKE_SCARCITY"|"FAKE_AUTHORITY"|"UNREALISTIC_RETURN"|"EMOTIONAL_PRESSURE"|"SOCIAL_PROOF_MANIPULATION">,
      "detected": <boolean>,
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
2. JANGAN gunakan enter/newline literal di dalam teks JSON. Gunakan \n untuk baris baru.
3. JANGAN gunakan kutip dua (") di dalam nilai string tanpa di-escape (\").
"""


# ── SENTRA Service ─────────────────────────────────────────────────────────────

class SentraService:
    """
    SENTRA AI service v2.1 — wraps Google Gemini 2.5 Flash (google-genai SDK).
    Features: Google Search Grounding, intelligence context injection, trap questions.
    Initialized once as a singleton at startup.
    """

    def __init__(self) -> None:
        self._model = settings.SENTRA_MODEL
        logger.info("SENTRA AI engine v2.1 initialized (model: %s, grounding: enabled)", self._model)

    async def _get_clients_and_models(self) -> list[tuple[genai.Client, str, bool]]:
        """
        Returns a list of tuples: (client, model_name, is_primary_key).
        Implements the API Key rotation logic based on the exhaustion state.
        """
        from app.services.cache_service import is_primary_api_key_exhausted
        
        is_exhausted = await is_primary_api_key_exhausted()
        clients_to_try = []
        
        primary_models = [self._model, settings.SENTRA_MODEL_BACKUP_1, "gemini-2.5-flash"]
        # Remove duplicates while preserving order, and ignore None/empty
        primary_models = list(dict.fromkeys([m for m in primary_models if m]))
        
        primary_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        backup_client = None
        if hasattr(settings, "GEMINI_API_KEY_BACKUP_1") and settings.GEMINI_API_KEY_BACKUP_1:
            backup_client = genai.Client(api_key=settings.GEMINI_API_KEY_BACKUP_1)
            
        if not is_exhausted:
            for m in primary_models:
                clients_to_try.append((primary_client, m, True))
                
        if backup_client:
            for m in primary_models:
                clients_to_try.append((backup_client, m, False))
                
        # If exhausted and no backup client available, we must try primary anyway as a last resort
        if not clients_to_try:
            for m in primary_models:
                clients_to_try.append((primary_client, m, True))
                
        return clients_to_try

    async def analyze(
        self,
        content: str,
        context_hint: str = "teks umum",
        intelligence_context: str = "",
    ) -> SentraAnalysisResult:
        """Run SENTRA analysis with automatic model fallback for robustness."""
        prompt = self._build_prompt(content, context_hint, intelligence_context)
        
        clients_and_models = await self._get_clients_and_models()
        last_exception = None
        from app.services.cache_service import mark_primary_api_key_exhausted
        
        for client, model_name, is_primary in clients_and_models:
            try:
                key_type = "PRIMARY" if is_primary else "BACKUP"
                logger.info("Attempting SENTRA analysis with model: %s on %s key", model_name, key_type)
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_PROMPT,
                        temperature=0.15,
                        top_p=0.85,
                        max_output_tokens=8192,
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                raw_json = response.text
                logger.debug("SENTRA raw output (first 300 chars): %s", raw_json[:300])
                return self._parse_response(raw_json)

            except Exception as exc:
                last_exception = exc
                error_msg = str(exc).lower()
                
                # If it's a rate limit or overloaded error, try next config
                if "429" in error_msg or "resource_exhausted" in error_msg or "overloaded" in error_msg:
                    logger.warning("Model %s on %s key is exhausted or overloaded. Trying next...", model_name, key_type)
                    
                    # If this is the last primary config we are trying, mark primary as exhausted
                    if is_primary:
                        remaining_primaries = [
                            c for c in clients_and_models[clients_and_models.index((client, model_name, is_primary))+1:] 
                            if c[2] # index 2 is is_primary
                        ]
                        if not remaining_primaries:
                            await mark_primary_api_key_exhausted()

                    await asyncio.sleep(1)
                    continue
                else:
                    # For other errors (like prompt blocked), don't retry, just raise
                    logger.exception("SENTRA analysis failed on model %s: %s", model_name, exc)
                    break

        # If all models failed
        logger.error("All SENTRA models exhausted or failed. Last error: %s", last_exception)
        raise ServiceUnavailableException(
            "SENTRA AI engine sedang sangat sibuk. Silakan coba lagi dalam beberapa saat."
        ) from last_exception

    async def extract_entities(self, content: str) -> list[str]:
        """
        Use Gemini to extract the main investment entity names from text.
        Includes fallback logic for rate limits.
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
        clients_and_models = await self._get_clients_and_models()
        from app.services.cache_service import mark_primary_api_key_exhausted

        for client, model_name, is_primary in clients_and_models:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text.replace("```json\n", "").replace("```", "").strip()
                
                entities = json.loads(text)
                if isinstance(entities, list):
                    return [str(e).strip() for e in entities if str(e).strip()][:3]
                return []
            except Exception as exc:
                error_msg = str(exc).lower()
                if "429" in error_msg or "resource_exhausted" in error_msg:
                    logger.warning("Entity extraction exhausted for model %s on %s key, trying fallback...", model_name, "PRIMARY" if is_primary else "BACKUP")
                    if is_primary:
                        remaining_primaries = [
                            c for c in clients_and_models[clients_and_models.index((client, model_name, is_primary))+1:] 
                            if c[2]
                        ]
                        if not remaining_primaries:
                            await mark_primary_api_key_exhausted()
                    continue
                logger.warning("Gemini entity extraction failed on %s: %s", model_name, exc)
                break
        
        return []

    async def chat(self, analysis_context: str, user_message: str) -> str:
        """
        AI Scam Guardian conversational response (PRD 5.4).
        Stateless: injects analysis context + user question into a single Gemini call.
        Returns plain text response in Bahasa Indonesia.
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

        clients_and_models = await self._get_clients_and_models()
        from app.services.cache_service import mark_primary_api_key_exhausted

        for client, model_name, is_primary in clients_and_models:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=chat_system_prompt,
                        temperature=0.3,
                        max_output_tokens=2048,
                    ),
                )
                return response.text or "Maaf, saya tidak dapat memproses pertanyaan ini saat ini."
            except Exception as exc:
                error_msg = str(exc).lower()
                if "429" in error_msg or "resource_exhausted" in error_msg or "overloaded" in error_msg:
                    logger.warning(
                        "SENTRA chat exhausted for model %s on %s key, trying fallback...",
                        model_name,
                        "PRIMARY" if is_primary else "BACKUP",
                    )
                    if is_primary:
                        remaining_primaries = [
                            c for c in clients_and_models[
                                clients_and_models.index((client, model_name, is_primary)) + 1:
                            ]
                            if c[2]
                        ]
                        if not remaining_primaries:
                            await mark_primary_api_key_exhausted()
                    continue
                logger.exception("SENTRA chat failed on model %s: %s", model_name, exc)
                break

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
