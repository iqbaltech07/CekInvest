"""
Chat router — AI Scam Guardian conversational endpoint (PRD 5.4).
Phase 1: stateless per-message, analysis context is injected each call.
No login required.
"""
from fastapi import APIRouter

from app.dependencies import DbDep, SentraDep
from app.schemas.common import APIResponse
from app.schemas.report import ChatMessageResponse, SendChatMessageRequest
from app.services import analysis_service
from app.utils.exceptions import NotFoundException

router = APIRouter(prefix="/chat", tags=["AI Scam Guardian"])


@router.post("/{analysis_id}", response_model=APIResponse[ChatMessageResponse])
async def send_chat_message(
    analysis_id: str,
    body: SendChatMessageRequest,
    sentra: SentraDep,
    db: DbDep,
):
    """
    Send a follow-up question to AI Scam Guardian about a specific analysis.
    PRD 5.4: 'Mengajukan pertanyaan lanjutan, mendapatkan template pesan konfirmasi.'
    No login required.
    """
    # Load analysis for context injection
    analysis = await analysis_service.get_analysis_by_id(analysis_id, db)

    # Build analysis context for SENTRA
    context = _build_analysis_context(analysis)

    # Get SENTRA's response
    ai_response = await sentra.chat(
        analysis_context=context,
        user_message=body.message,
    )

    # Persist conversation to ChatSession
    session = await db.chatsession.find_first(
        where={"analysisId": analysis_id},
        order={"createdAt": "desc"},
    )
    if session is None:
        session = await db.chatsession.create(
            data={"analysisId": analysis_id}
        )

    # Save user message
    await db.chatmessage.create(
        data={
            "sessionId": session.id,
            "role": "USER",
            "content": body.message,
        }
    )

    # Save assistant response and return it
    assistant_msg = await db.chatmessage.create(
        data={
            "sessionId": session.id,
            "role": "ASSISTANT",
            "content": ai_response,
        }
    )

    from app.schemas.report import ChatMessageRole
    from datetime import datetime, timezone
    return APIResponse(
        data=ChatMessageResponse(
            id=assistant_msg.id,
            role=ChatMessageRole.ASSISTANT,
            content=ai_response,
            createdAt=assistant_msg.createdAt,
        )
    )


@router.get("/{analysis_id}/history", response_model=APIResponse[list[ChatMessageResponse]])
async def get_chat_history(analysis_id: str, db: DbDep):
    """Get conversation history for an analysis session."""
    session = await db.chatsession.find_first(
        where={"analysisId": analysis_id},
        order={"createdAt": "desc"},
    )
    if session is None:
        return APIResponse(data=[])

    messages = await db.chatmessage.find_many(
        where={"sessionId": session.id},
        order={"createdAt": "asc"},
    )
    from app.schemas.report import ChatMessageRole
    return APIResponse(
        data=[
            ChatMessageResponse(
                id=m.id,
                role=ChatMessageRole(m.role),
                content=m.content,
                createdAt=m.createdAt,
            )
            for m in messages
        ]
    )


def _build_analysis_context(analysis) -> str:
    """Format analysis data as context for AI Scam Guardian."""
    flags_text = ""
    if hasattr(analysis, "redFlags") and analysis.redFlags:
        flags = [f"- [{f.severity}] {f.category}: {f.description}" for f in analysis.redFlags[:5]]
        flags_text = "\nRed Flags:\n" + "\n".join(flags)

    ojk_text = f"\nStatus OJK: {analysis.ojkStatus}" if analysis.ojkStatus else ""
    domain_text = (
        f"\nDomain berumur {analysis.domainAgeDays} hari"
        if analysis.domainAgeDays is not None else ""
    )

    return (
        f"Hasil analisis SENTRA:\n"
        f"Risk Score: {analysis.riskScore}/100 ({analysis.riskLevel})\n"
        f"Ringkasan: {analysis.summary or 'Tidak ada ringkasan.'}\n"
        f"Penjelasan: {analysis.explanation or ''}\n"
        f"{ojk_text}{domain_text}{flags_text}"
    )
