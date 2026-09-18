"""Routers package — all public, no auth required."""
from app.routers.analysis import router as analysis_router
from app.routers.reports import router as reports_router
from app.routers.intelligence import router as intelligence_router
from app.routers.share import router as share_router
from app.routers.chat import router as chat_router
from app.routers.clustering import router as clustering_router
from app.routers.ml_router import ml_router

__all__ = [
    "analysis_router",
    "reports_router",
    "intelligence_router",
    "share_router",
    "chat_router",
    "clustering_router",
    "ml_router",
]

