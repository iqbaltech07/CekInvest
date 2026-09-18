import asyncio
import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from prisma import Prisma


from ml.constants import (
    GNN_METADATA_PATH,
    MODELS_DIR,
    TRAINING_LOG_PATH,
    VISUALIZATION_PLOT_PATH,
    EPOCHS,
    LEARNING_RATE,
    TEST_SPLIT,
    VAL_SPLIT,
)

logger = logging.getLogger(__name__)

ml_router = APIRouter(prefix="", tags=["Machine Learning"])

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "ml" / "templates"
DATA_DIR = Path(__file__).parent.parent.parent / "ml" / "data"
TEMPLATE_PATH = DATA_DIR / "sample_dataset_template.csv"
TOPOLOGY_PATH = MODELS_DIR / "gnn_graph_topology.json"



@ml_router.get(
    "/ml/dashboard",
    response_class=HTMLResponse,
    summary="Interactive GNN Training Visualizer Dashboard",
)
async def get_training_dashboard():
    """Serves the interactive GNN real-time training and topology visualizer."""
    dashboard_file = TEMPLATES_DIR / "train_dashboard.html"
    if not dashboard_file.exists():
        return HTMLResponse(
            content="<h1>Visualizer template not found</h1>",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    with open(dashboard_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@ml_router.get(
    "/ml/graph-topology",
    summary="Get Heterogeneous Graph Topology (Nodes & Edges)",
)
async def get_graph_topology():
    """Returns nodes and edges for Vis.js interactive network graph.
    If topology file has not yet been exported, gracefully constructs topology
    directly from active database clusters so it never crashes with 404/500."""
    if TOPOLOGY_PATH.exists():
        try:
            with open(TOPOLOGY_PATH, "r", encoding="utf-8") as f:
                topology_data = json.load(f)
            return JSONResponse(content=topology_data)
        except Exception as exc:
            logger.warning("Failed to read topology file, falling back to DB: %s", exc)

    # ── Graceful Fallback: Build topology dynamically from ScamCluster DB ───
    try:
        from app.database import prisma
        if not prisma.is_connected():
            await prisma.connect()

        clusters = await prisma.scamcluster.find_many()
        if not clusters:
            return JSONResponse(content={
                "nodes": [],
                "edges": [],
                "stats": {"total_nodes": 0, "total_edges": 0, "reports": 0, "banks": 0, "phones": 0, "domains": 0},
            })

        nodes_dict: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        for c in clusters:
            c_node_id = f"cluster_{c.id}"
            nodes_dict[c_node_id] = {
                "id": c_node_id,
                "label": c.groupName[:28] + ("..." if len(c.groupName) > 28 else ""),
                "group": "scam" if c.riskLevel in ("HIGH", "CRITICAL") else "warning",
                "title": f"<b>{c.groupName}</b><br>Kategori: {c.category}<br>Total Laporan: {c.totalReports}",
                "category": c.category,
                "isScam": True,
            }

            for b in (c.bankAccounts or []):
                b_node_id = f"bank_{b}"
                nodes_dict.setdefault(b_node_id, {
                    "id": b_node_id,
                    "label": b,
                    "group": "bank",
                    "title": f"<b>Rekening Bank:</b> {b}",
                })
                edges.append({"from": c_node_id, "to": b_node_id, "label": "mentions_account", "color": {"color": "#06B6D4"}})

            for p in (c.phoneNumbers or []):
                p_node_id = f"phone_{p}"
                nodes_dict.setdefault(p_node_id, {
                    "id": p_node_id,
                    "label": p,
                    "group": "phone",
                    "title": f"<b>Nomor Telepon:</b> {p}",
                })
                edges.append({"from": c_node_id, "to": p_node_id, "label": "mentions_phone", "color": {"color": "#F59E0B"}})

            for d in (c.domains or []):
                d_node_id = f"domain_{d}"
                nodes_dict.setdefault(d_node_id, {
                    "id": d_node_id,
                    "label": d,
                    "group": "domain",
                    "title": f"<b>Domain/URL:</b> {d}",
                })
                edges.append({"from": c_node_id, "to": d_node_id, "label": "mentions_domain", "color": {"color": "#A855F7"}})

        nodes_list = list(nodes_dict.values())
        return JSONResponse(content={
            "nodes": nodes_list,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes_list),
                "total_edges": len(edges),
                "reports": len(clusters),
                "scam_reports": len(clusters),
                "legit_reports": 0,
                "banks": sum(1 for n in nodes_list if n.get("group") == "bank"),
                "phones": sum(1 for n in nodes_list if n.get("group") == "phone"),
                "domains": sum(1 for n in nodes_list if n.get("group") == "domain"),
            }
        })

    except Exception as exc:
        logger.exception("Failed to build fallback graph topology: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "nodes": [],
                "edges": [],
                "stats": {"total_nodes": 0, "total_edges": 0, "reports": 0},
                "warning": f"Graf topologi sedang disiapkan: {str(exc)}",
            },
        )


@ml_router.get(
    "/ml/training-status",
    summary="Get latest GNN training metrics and metadata",
)
async def get_training_status():
    """Returns the latest training history log and graph metadata."""
    log_data = {}
    if TRAINING_LOG_PATH.exists():
        with open(TRAINING_LOG_PATH, "r", encoding="utf-8") as f:
            log_data = json.load(f)

    meta_data = {}
    if GNN_METADATA_PATH.exists():
        with open(GNN_METADATA_PATH, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

    return {
        "success": True,
        "data": {
            "training_log": log_data,
            "metadata": meta_data,
            "has_model": (MODELS_DIR / "gnn_model.pt").exists(),
            "has_plot": VISUALIZATION_PLOT_PATH.exists(),
        },
    }


@ml_router.get(
    "/ml/train-stream",
    summary="Stream live GNN training progress per epoch (SSE)",
)
async def stream_training(
    epochs: int = Query(EPOCHS, ge=5, le=300),
    lr: float = Query(LEARNING_RATE, ge=0.0001, le=0.1),
    test_split: float = Query(TEST_SPLIT, ge=0.05, le=0.40),
    val_split: float = Query(VAL_SPLIT, ge=0.05, le=0.40),
):
    """
    Streams Server-Sent Events (SSE) emitting training loss and accuracy metrics
    per epoch in real-time as the GNN model learns.
    """
    from ml.train_sage import train_generator

    async def sse_event_stream():
        try:
            # Run generator with dynamic split
            generator = train_generator(
                epochs=epochs,
                lr=lr,
                test_split=test_split,
                val_split=val_split,
                live_plot=False,
            )
            for step in generator:
                payload = json.dumps(step)
                yield f"data: {payload}\n\n"
                # Brief sleep to yield execution to the asyncio event loop
                await asyncio.sleep(0.02)
        except Exception as exc:
            logger.exception("Error during live training stream: %s", exc)
            err_payload = json.dumps({"event": "error", "message": str(exc)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@ml_router.get(
    "/ml/visualization-plot",
    summary="Download or view generated training visualization PNG plot",
)
async def get_visualization_plot():
    """Returns the high-resolution Matplotlib training plot PNG."""
    if not VISUALIZATION_PLOT_PATH.exists():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "error": "Visualization plot not found. Run training first."},
        )
    return FileResponse(
        VISUALIZATION_PLOT_PATH,
        media_type="image/png",
        filename="training_visualization.png",
    )


@ml_router.get(
    "/ml/download-template",
    summary="Download CSV dataset template for training",
)
async def download_dataset_template():
    """Returns the sample CSV dataset template for user uploads."""
    if not TEMPLATE_PATH.exists():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "error": "Template file not found."},
        )
    return FileResponse(
        TEMPLATE_PATH,
        media_type="text/csv",
        filename="sample_dataset_template.csv",
    )


@ml_router.post(
    "/ml/upload-dataset",
    summary="Upload new training dataset (CSV or JSON) and update GNN graph",
)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV or JSON file containing financial communication reports,
    saves them to UserReport database, and automatically updates the GNN graph.
    """
    filename = file.filename or ""
    if not (filename.endswith(".csv") or filename.endswith(".json")):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Hanya file berekstensi .csv atau .json yang didukung."},
        )

    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8-sig", errors="replace")

        records_to_insert = []

        if filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content_str))
            for row in reader:
                # normalize keys to lowercase without whitespace
                norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                text = norm_row.get("text") or norm_row.get("rawinput") or norm_row.get("pesan") or norm_row.get("content")
                if not text:
                    continue

                val_scam = norm_row.get("is_scam", norm_row.get("isscam", norm_row.get("scam", norm_row.get("label", "0"))))
                is_scam = str(val_scam).lower() in ("1", "true", "yes", "ya", "t", "scam")

                category = norm_row.get("category") or norm_row.get("scamcategory") or ("Investasi Bodong" if is_scam else "Legal")
                bank_name = norm_row.get("bank_name") or norm_row.get("bankname") or None
                bank_account = norm_row.get("bank_account") or norm_row.get("bankaccount") or None
                phone = norm_row.get("phone") or norm_row.get("phonenumber") or None
                domain = norm_row.get("domain") or None

                records_to_insert.append({
                    "rawInput": text,
                    "inputType": "CHAT",
                    "isScam": is_scam,
                    "scamCategory": category,
                    "bankName": bank_name,
                    "bankAccount": bank_account,
                    "phoneNumber": phone,
                    "domain": domain,
                })

        elif filename.endswith(".json"):
            parsed_json = json.loads(content_str)
            raw_list = parsed_json if isinstance(parsed_json, list) else parsed_json.get("data", [])
            for item in raw_list:
                norm_item = {str(k).strip().lower(): str(v).strip() for k, v in item.items() if k}
                text = norm_item.get("text") or norm_item.get("rawinput") or norm_item.get("pesan")
                if not text:
                    continue

                val_scam = norm_item.get("is_scam", norm_item.get("isscam", norm_item.get("scam", norm_item.get("label", "0"))))
                is_scam = str(val_scam).lower() in ("1", "true", "yes", "ya", "t", "scam")
                category = norm_item.get("category") or norm_item.get("scamcategory") or ("Investasi Bodong" if is_scam else "Legal")

                records_to_insert.append({
                    "rawInput": text,
                    "inputType": "CHAT",
                    "isScam": is_scam,
                    "scamCategory": category,
                    "bankName": norm_item.get("bank_name") or norm_item.get("bankname") or None,
                    "bankAccount": norm_item.get("bank_account") or norm_item.get("bankaccount") or None,
                    "phoneNumber": norm_item.get("phone") or norm_item.get("phonenumber") or None,
                    "domain": norm_item.get("domain") or None,
                })


        if not records_to_insert:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Tidak ada baris data valid yang ditemukan dalam file (kolom 'text' atau 'rawInput' wajib diisi)."},
            )

        # Insert into database using app singleton prisma
        from app.database import prisma
        if not prisma.is_connected():
            await prisma.connect()
        
        inserted_count = 0
        for rec in records_to_insert:
            await prisma.userreport.create(data=rec)
            inserted_count += 1

        total_reports = await prisma.userreport.count()

        # Re-export graph to synchronize PyG HeteroData and visual topology
        from ml.export_graph import export_graph
        await export_graph()

        logger.info("Successfully imported %d new reports. Total in DB: %d", inserted_count, total_reports)


        return {
            "success": True,
            "message": f"Berhasil mengunggah {inserted_count} data laporan baru. Topologi graf telah diperbarui dan siap di-train ulang!",
            "data": {
                "inserted_count": inserted_count,
                "total_reports": total_reports,
            },
        }

    except Exception as exc:
        logger.exception("Error uploading dataset: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Gagal memproses file: {str(exc)}"},
        )


@ml_router.get(
    "/ml/export-dataset",
    summary="Export all collected user reports as a training dataset (CSV or JSON)",
)
async def export_dataset(format: str = Query("csv", pattern="^(csv|json)$")):
    """
    Exports all UserReport records from the database into a clean dataset file (CSV or JSON)
    for offline inspection, data quality curation, labeling, or re-training.
    """
    try:
        from app.database import prisma
        if not prisma.is_connected():
            await prisma.connect()

        reports = await prisma.userreport.find_many(order={"createdAt": "desc"})

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == "json":
            data = [
                {
                    "text": r.rawInput,
                    "is_scam": 1 if r.isScam else 0,
                    "category": r.scamCategory or ("Investasi Bodong" if r.isScam else "Legal"),
                    "bank_name": r.bankName,
                    "bank_account": r.bankAccount,
                    "phone": r.phoneNumber,
                    "domain": r.domain,
                    "created_at": r.createdAt.isoformat() if r.createdAt else None,
                }
                for r in reports
            ]
            filename = f"cekinvest_dataset_{timestamp}.json"
            return Response(
                content=json.dumps(data, indent=2, ensure_ascii=False),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        # Default: CSV
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["text", "is_scam", "category", "bank_name", "bank_account", "phone", "domain", "created_at"])

        for r in reports:
            writer.writerow([
                r.rawInput or "",
                1 if r.isScam else 0,
                r.scamCategory or ("Investasi Bodong" if r.isScam else "Legal"),
                r.bankName or "",
                r.bankAccount or "",
                r.phoneNumber or "",
                r.domain or "",
                r.createdAt.isoformat() if r.createdAt else "",
            ])

        filename = f"cekinvest_dataset_{timestamp}.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as exc:
        logger.exception("Error exporting dataset: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Gagal mengekspor dataset: {str(exc)}"},
        )


@ml_router.post(
    "/ml/sync-database-graph",
    summary="Synchronize database user reports directly into PyG graph, scam_clusters, and pgvector RAG store",
)
async def sync_database_graph():
    """
    Unified Sync Pipeline — triggers all three synchronization steps in one click:
    1. Exports all UserReports into PyG HeteroData graph and Vis.js topology
    2. Runs GNN Connected Components to populate/update scam_clusters table
    3. Embeds all UserReports and ScamPatterns into pgvector RAG knowledge base
    """
    try:
        from app.database import prisma
        if not prisma.is_connected():
            await prisma.connect()

        total_reports = await prisma.userreport.count()
        total_clusters_before = await prisma.scamcluster.count()
        total_patterns = await prisma.scampattern.count()

        from ml.export_graph import export_graph
        await export_graph()

        total_clusters_after = await prisma.scamcluster.count()
        new_clusters = total_clusters_after - total_clusters_before

        return {
            "success": True,
            "message": (
                f"✅ Sinkronisasi selesai! {total_reports} laporan → Graf GNN diperbarui, "
                f"{total_clusters_after} klaster aktif ({new_clusters:+d} baru), "
                f"{total_patterns} pola penipuan di-embed ke RAG."
            ),
            "data": {
                "total_reports": total_reports,
                "total_clusters": total_clusters_after,
                "new_clusters_detected": new_clusters,
                "patterns_in_knowledge_base": total_patterns,
            },
        }
    except Exception as exc:
        logger.exception("Error synchronizing database graph: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"Gagal menyinkronkan graf: {str(exc)}"},
        )


