"""
Analysis router v2.1 — SENTRA AI analysis endpoints.
Adds: SSE streaming endpoint for progressive real-time analysis feedback.
All endpoints fully public. No login required.
"""
import asyncio
import json

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from prisma.enums import InputType

from app.dependencies import DbDep, SentraDep
from app.schemas.analysis import AnalysisResponse, ChatAnalysisRequest, UrlAnalysisRequest
from app.schemas.common import APIResponse
from app.services import analysis_service
from app.utils.exceptions import BadRequestException

router = APIRouter(prefix="/analysis", tags=["Analysis"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/chat", response_model=APIResponse[AnalysisResponse], status_code=201)
async def analyze_chat(body: ChatAnalysisRequest, sentra: SentraDep, db: DbDep):
    """
    Analyze pasted chat messages or suspicious text through the SENTRA pipeline.
    Supports WhatsApp, Telegram, SMS, or any text.
    Includes: OJK check, emotional manipulation detection, trap questions, shareable slug.
    No login required.
    """
    analysis = await analysis_service.analyze_chat(body.text, sentra, db)
    return APIResponse(data=AnalysisResponse.model_validate(analysis, from_attributes=True))


@router.post("/screenshot", response_model=APIResponse[AnalysisResponse], status_code=201)
async def analyze_screenshot(
    sentra: SentraDep,
    db: DbDep,
    file: UploadFile = File(..., description="Screenshot image (JPEG, PNG, WEBP — max 10MB)"),
):
    """
    Upload a screenshot image. SENTRA extracts text via Tesseract OCR then analyzes.
    No login required.
    """
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise BadRequestException(
            f"Tipe file tidak didukung: {file.content_type}. Gunakan JPEG, PNG, atau WEBP."
        )
    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
        raise BadRequestException("Ukuran file terlalu besar. Maksimum 10MB.")

    analysis = await analysis_service.analyze_screenshot(image_bytes, sentra, db)
    return APIResponse(data=AnalysisResponse.model_validate(analysis, from_attributes=True))


@router.post("/url", response_model=APIResponse[AnalysisResponse], status_code=201)
async def analyze_url(body: UrlAnalysisRequest, sentra: SentraDep, db: DbDep):
    """
    Analyze a suspicious investment URL.
    SENTRA fetches page content, runs WHOIS domain intel, and analyzes with Google Grounding.
    No login required.
    """
    analysis = await analysis_service.analyze_url(body.url, sentra, db)
    return APIResponse(data=AnalysisResponse.model_validate(analysis, from_attributes=True))


@router.get("/{analysis_id}", response_model=APIResponse[AnalysisResponse])
async def get_analysis(analysis_id: str, db: DbDep):
    """Retrieve a specific analysis result by its ID. No login required."""
    analysis = await analysis_service.get_analysis_by_id(analysis_id, db)
    return APIResponse(data=AnalysisResponse.model_validate(analysis, from_attributes=True))


# ── SSE Streaming Endpoint ────────────────────────────────────────────────────

@router.post("/stream/chat")
async def stream_analyze_chat(body: ChatAnalysisRequest, sentra: SentraDep, db: DbDep):
    """
    Server-Sent Events streaming endpoint for real-time analysis feedback.
    PRD: 'Streaming response dimulai sebelum semua 23 checks selesai.'
    User sees progressive updates: extracting → checking OJK → analyzing → complete.

    Returns: text/event-stream with JSON stage events.
    """
    async def event_generator():
        try:
            # Stage 1: Acknowledge input
            yield _sse_event("stage", {"stage": "received", "message": "Input diterima, memulai analisis..."})
            await asyncio.sleep(0.05)

            # Stage 2: Intelligence checks starting
            yield _sse_event("stage", {"stage": "intelligence", "message": "Memeriksa database OJK, domain, dan berita media..."})

            # Run intelligence checks
            from app.services.intelligence_orchestrator import run_parallel_checks
            intel = await run_parallel_checks(
                content=body.text, input_type="CHAT", url=None, db=db, sentra=sentra
            )

            # Stream intelligence findings as they complete
            ojk_msg = f"Status OJK: {intel.ojk_status}"
            yield _sse_event("intelligence", {
                "stage": "intelligence_complete",
                "ojk_status": intel.ojk_status,
                "message": ojk_msg,
                "has_young_domain": intel.has_young_domain_flag,
                "negative_news_count": intel.negative_news_count,
            })

            # Stage 3: SENTRA AI Analysis
            yield _sse_event("stage", {"stage": "analyzing", "message": "SENTRA AI sedang menganalisis pola manipulasi..."})

            from app.services.cache_service import cache_get, make_analysis_key
            cache_key = make_analysis_key(body.text)
            cached_id = await cache_get(cache_key)

            if cached_id:
                yield _sse_event("stage", {"stage": "cache_hit", "message": "Analisis identik ditemukan di cache — hasil instan!"})
                analysis = await db.analysis.find_unique(
                    where={"id": cached_id},
                    include={"redFlags": True, "emotionSignals": True},
                )
                if analysis:
                    yield _sse_event("complete", AnalysisResponse.model_validate(
                        analysis, from_attributes=True
                    ).model_dump(mode="json"))
                    return

            # Full SENTRA analysis
            sentra_result = await sentra.analyze(
                content=body.text,
                context_hint="chat WhatsApp/Telegram",
                intelligence_context=intel.to_prompt_context(),
            )

            # Stage 4: Persisting
            yield _sse_event("stage", {"stage": "saving", "message": "Menyimpan hasil analisis..."})

            analysis = await analysis_service._persist_analysis(
                raw_input=body.text,
                input_type=InputType.CHAT,
                extracted_text=body.text,
                sentra_result=sentra_result,
                intel=intel,
                db=db,
            )

            # Stage 5: Complete
            yield _sse_event("complete", AnalysisResponse.model_validate(
                analysis, from_attributes=True
            ).model_dump(mode="json"))

        except Exception as exc:
            yield _sse_event("error", {"message": str(exc), "stage": "error"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
