"""
Export graph data from Prisma database to PyTorch Geometric format.
Run: python -m ml.export_graph
Output: 
  - ml/models/gnn_dataset.pt
  - ml/models/tfidf_vectorizer.pkl
  - ml/models/gnn_metadata.json
"""
import asyncio
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
from prisma import Prisma
from sklearn.feature_extraction.text import TfidfVectorizer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.constants import (
    GRAPH_DATASET_PATH,
    MODELS_DIR,
    REPORT_FEAT_DIM,
    ACCOUNT_FEAT_DIM,
    PHONE_FEAT_DIM,
    DOMAIN_FEAT_DIM,
    SIMILARITY_THRESHOLD,
    RANDOM_SEED,
)
from ml.utils import (
    extract_phone_numbers,
    extract_bank_accounts,
    extract_domains,
    compute_text_similarity,
    compute_account_features,
    normalize_text,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

try:
    import torch
    torch.manual_seed(RANDOM_SEED)
except ImportError:
    pass
np.random.seed(RANDOM_SEED)


async def export_graph() -> Any:
    """Export Prisma data to PyG HeteroData graph structure."""
    from app.database import prisma
    should_disconnect = False
    if not prisma.is_connected():
        await prisma.connect()
        should_disconnect = True
    db = prisma
    
    logger.info("Fetching data from database...")

    reports = await db.userreport.find_many()
    logger.info(f"Fetched {len(reports)} UserReports")
    
    if not reports:
        raise ValueError("No UserReports found in database. Run seed script first.")
    
    # ── Fit and save TF-IDF Vectorizer ──────────────────────────────────────
    corpus = [normalize_text(r.rawInput) for r in reports]
    vectorizer = TfidfVectorizer(
        max_features=REPORT_FEAT_DIM,
        min_df=1,
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(corpus).toarray()
    
    vectorizer_path = MODELS_DIR / "tfidf_vectorizer.pkl"
    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)
    logger.info(f"✅ Saved TF-IDF vectorizer to {vectorizer_path}")

    # ── Extract entities from reports ────────────────────────────────────────
    report_entities: list[dict[str, Any]] = []
    all_banks: dict[str, set[str]] = {}
    all_phones: dict[str, set[str]] = {}
    all_domains: dict[str, set[str]] = {}
    
    for r in reports:
        phones = extract_phone_numbers(r.rawInput)
        banks = extract_bank_accounts(r.rawInput)
        domains = extract_domains(r.rawInput)
        
        entities = {
            "report_id": r.id,
            "is_scam": r.isScam,
            "category": r.scamCategory,
            "phones": phones,
            "banks": banks,
            "domains": domains,
            "raw_text": r.rawInput,
        }
        report_entities.append(entities)
        
        for phone in phones:
            all_phones.setdefault(phone, set()).add(r.id)
        for bank_name, account in banks:
            all_banks.setdefault(f"{bank_name}:{account}", set()).add(r.id)
        for domain in domains:
            all_domains.setdefault(domain, set()).add(r.id)
            
    bank_id_to_idx = {b: i for i, b in enumerate(all_banks)}
    phone_id_to_idx = {p: i for i, p in enumerate(all_phones)}
    domain_id_to_idx = {d: i for i, d in enumerate(all_domains)}
    
    # ── Build node feature arrays (pure numpy, independent of PyTorch) ───────
    feat_report = np.zeros((len(reports), REPORT_FEAT_DIM), dtype=np.float32)
    for i, r in enumerate(reports):
        feat_report[i] = tfidf_matrix[i]

    feat_bank = np.zeros((max(1, len(all_banks)), ACCOUNT_FEAT_DIM), dtype=np.float32)
    for bank_id, idx in bank_id_to_idx.items():
        feat_bank[idx] = compute_account_features(len(all_banks[bank_id]), None)

    feat_phone = np.zeros((max(1, len(all_phones)), PHONE_FEAT_DIM), dtype=np.float32)
    for phone, idx in phone_id_to_idx.items():
        feat_phone[idx] = compute_account_features(len(all_phones[phone]), None)

    feat_domain = np.zeros((max(1, len(all_domains)), DOMAIN_FEAT_DIM), dtype=np.float32)
    for domain, idx in domain_id_to_idx.items():
        feat_domain[idx] = compute_account_features(len(all_domains[domain]), None)

    # ── Build edges ──────────────────────────────────────────────────────────
    report_to_bank_edges = []
    for r_idx, entities in enumerate(report_entities):
        for bank_name, account in entities["banks"]:
            key = f"{bank_name}:{account}"
            if key in bank_id_to_idx:
                report_to_bank_edges.append((r_idx, bank_id_to_idx[key]))
                
    report_to_phone_edges = []
    for r_idx, entities in enumerate(report_entities):
        for phone in entities["phones"]:
            if phone in phone_id_to_idx:
                report_to_phone_edges.append((r_idx, phone_id_to_idx[phone]))
                
    report_to_domain_edges = []
    for r_idx, entities in enumerate(report_entities):
        for domain in entities["domains"]:
            if domain in domain_id_to_idx:
                report_to_domain_edges.append((r_idx, domain_id_to_idx[domain]))

    # Reverse edges so information flows INTO Report from entities
    bank_to_report_edges = [(dst, src) for src, dst in report_to_bank_edges]
    phone_to_report_edges = [(dst, src) for src, dst in report_to_phone_edges]
    domain_to_report_edges = [(dst, src) for src, dst in report_to_domain_edges]

    # Fast matrix-based text cosine similarity (O(1) matrix op instead of O(N^2) fit_transforms)
    from sklearn.metrics.pairwise import cosine_similarity
    sim_matrix = cosine_similarity(tfidf_matrix)

    report_to_report_edges = []
    for i in range(len(reports)):
        for j in range(i + 1, len(reports)):
            if sim_matrix[i, j] >= SIMILARITY_THRESHOLD:
                report_to_report_edges.append((i, j))
                report_to_report_edges.append((j, i))

    # Self-loops on Report nodes (guarantees text features are preserved even if isolated)
    report_self_loops = [(i, i) for i in range(len(reports))]

    # ── Format HeteroData (if PyTorch & PyG are installed) ───────────────────
    graph = None
    try:
        import torch
        from torch_geometric.data import HeteroData

        x_report = torch.from_numpy(feat_report).float()
        x_bank = torch.from_numpy(feat_bank).float()
        x_phone = torch.from_numpy(feat_phone).float()
        x_domain = torch.from_numpy(feat_domain).float()

        graph = HeteroData()
        graph["Report"].x = x_report
        graph["BankAccount"].x = x_bank
        graph["Phone"].x = x_phone
        graph["Domain"].x = x_domain

        def to_edge_tensor(edges):
            if not edges:
                return torch.empty((2, 0), dtype=torch.long)
            return torch.tensor(edges, dtype=torch.long).T

        graph["Report", "mentions_account", "BankAccount"].edge_index = to_edge_tensor(report_to_bank_edges)
        graph["Report", "mentions_phone", "Phone"].edge_index = to_edge_tensor(report_to_phone_edges)
        graph["Report", "mentions_domain", "Domain"].edge_index = to_edge_tensor(report_to_domain_edges)

        # Incoming edges from entities into Report
        graph["BankAccount", "mentioned_in", "Report"].edge_index = to_edge_tensor(bank_to_report_edges)
        graph["Phone", "mentioned_in", "Report"].edge_index = to_edge_tensor(phone_to_report_edges)
        graph["Domain", "mentioned_in", "Report"].edge_index = to_edge_tensor(domain_to_report_edges)

        graph["Report", "similar_content", "Report"].edge_index = to_edge_tensor(report_to_report_edges)
        graph["Report", "self_loop", "Report"].edge_index = to_edge_tensor(report_self_loops)

        # Labels
        graph["Report"].y = torch.tensor([1 if r.isScam else 0 for r in reports], dtype=torch.long)
        
        # Save graph & metadata
        GRAPH_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        torch.save(graph, GRAPH_DATASET_PATH)
        
        metadata = {
            "node_types": graph.node_types,
            "edge_types": [list(edge) for edge in graph.edge_types],
        }
        with open(MODELS_DIR / "gnn_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ PyG HeteroData saved to {GRAPH_DATASET_PATH}")
    except ImportError:
        logger.info("ℹ️ PyTorch / PyG not installed. HeteroData export skipped (safe for Render Free 512MB RAM mode).")
    except Exception as gnn_save_exc:
        logger.warning("GNN HeteroData export encountered an issue: %s", gnn_save_exc)
        
    # Save topology for interactive web visualizer
    topology_nodes = []
    topology_edges = []

    for i, r in enumerate(reports):
        is_scam = bool(r.isScam)
        topology_nodes.append({
            "id": f"report_{i}",
            "label": f"Report #{i+1}",
            "group": "scam" if is_scam else "legit",
            "title": f"<b>{'[SCAM]' if is_scam else '[LEGIT]'} {r.scamCategory or 'General'}</b><br>{(r.rawInput or '')[:120]}...",
            "category": r.scamCategory or "General",
            "isScam": is_scam,
            "rawText": (r.rawInput or "")[:240],
        })

    for b_key, b_idx in bank_id_to_idx.items():
        topology_nodes.append({
            "id": f"bank_{b_idx}",
            "label": b_key,
            "group": "bank",
            "title": f"<b>Rekening Bank:</b> {b_key}",
        })

    for p_key, p_idx in phone_id_to_idx.items():
        topology_nodes.append({
            "id": f"phone_{p_idx}",
            "label": p_key,
            "group": "phone",
            "title": f"<b>Nomor Telepon:</b> {p_key}",
        })

    for d_key, d_idx in domain_id_to_idx.items():
        topology_nodes.append({
            "id": f"domain_{d_idx}",
            "label": d_key,
            "group": "domain",
            "title": f"<b>Domain/URL:</b> {d_key}",
        })

    for r_idx, b_idx in report_to_bank_edges:
        topology_edges.append({"from": f"report_{r_idx}", "to": f"bank_{b_idx}", "label": "mentions_account", "color": {"color": "#06B6D4"}})

    for r_idx, p_idx in report_to_phone_edges:
        topology_edges.append({"from": f"report_{r_idx}", "to": f"phone_{p_idx}", "label": "mentions_phone", "color": {"color": "#F59E0B"}})

    for r_idx, d_idx in report_to_domain_edges:
        topology_edges.append({"from": f"report_{r_idx}", "to": f"domain_{d_idx}", "label": "mentions_domain", "color": {"color": "#A855F7"}})

    for r1, r2 in report_to_report_edges:
        topology_edges.append({"from": f"report_{r1}", "to": f"report_{r2}", "label": "similar_text", "color": {"color": "#64748B", "opacity": 0.4}})

    topology_path = MODELS_DIR / "gnn_graph_topology.json"
    with open(topology_path, "w", encoding="utf-8") as f:
        json.dump({
            "nodes": topology_nodes,
            "edges": topology_edges,
            "stats": {
                "total_nodes": len(topology_nodes),
                "reports": len(reports),
                "scam_reports": sum(1 for r in reports if r.isScam),
                "legit_reports": sum(1 for r in reports if not r.isScam),
                "banks": len(bank_id_to_idx),
                "phones": len(phone_id_to_idx),
                "domains": len(domain_id_to_idx),
                "total_edges": len(topology_edges),
            }
        }, f, indent=2)
    logger.info(f"✅ Visual topology saved to {topology_path}")

    # ── Sync embeddings to pgvector store (gemini-embedding-001) ─────────────
    try:
        from app.services.rag_service import rag_service
        await rag_service.sync_all_reports_to_vector_store(db)
    except Exception as rag_sync_exc:
        logger.warning("RAG vector store sync skipped or non-fatal: %s", rag_sync_exc)

    # ── Sync GNN Connected Components → scam_clusters table ──────────────────
    try:
        await _sync_clusters_to_database(
            db=db,
            reports=reports,
            report_entities=report_entities,
            report_to_bank_edges=report_to_bank_edges,
            report_to_phone_edges=report_to_phone_edges,
            report_to_domain_edges=report_to_domain_edges,
            report_to_report_edges=report_to_report_edges,
        )
    except Exception as cluster_sync_exc:
        logger.warning("Cluster sync skipped or non-fatal: %s", cluster_sync_exc)

    if should_disconnect:
        await db.disconnect()
    return graph


async def _sync_clusters_to_database(
    db,
    reports,
    report_entities,
    report_to_bank_edges,
    report_to_phone_edges,
    report_to_domain_edges,
    report_to_report_edges,
) -> int:
    """
    Runs Union-Find Connected Components on the heterogeneous graph
    and upserts the resulting groups into the `scam_clusters` table.

    This makes `scam_clusters` a direct output of GNN graph analysis,
    eliminating the separate/duplicated clustering algorithm.
    """
    n = len(reports)
    if n == 0:
        return 0

    # ── Union-Find (Disjoint Set Union) ──────────────────────────────────────
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Connect reports that share bank account nodes
    bank_to_reports: dict[int, list[int]] = {}
    for r_idx, b_idx in report_to_bank_edges:
        bank_to_reports.setdefault(b_idx, []).append(r_idx)
    for grp in bank_to_reports.values():
        for i in range(1, len(grp)):
            union(grp[0], grp[i])

    # Connect reports that share phone number nodes
    phone_to_reports: dict[int, list[int]] = {}
    for r_idx, p_idx in report_to_phone_edges:
        phone_to_reports.setdefault(p_idx, []).append(r_idx)
    for grp in phone_to_reports.values():
        for i in range(1, len(grp)):
            union(grp[0], grp[i])

    # Connect reports that share domain nodes
    domain_to_reports: dict[int, list[int]] = {}
    for r_idx, d_idx in report_to_domain_edges:
        domain_to_reports.setdefault(d_idx, []).append(r_idx)
    for grp in domain_to_reports.values():
        for i in range(1, len(grp)):
            union(grp[0], grp[i])

    # Connect reports with high text similarity (already computed)
    for r1, r2 in report_to_report_edges:
        if r1 < r2:  # avoid double-processing bidirectional edges
            union(r1, r2)

    # ── Group reports by root ─────────────────────────────────────────────────
    from collections import defaultdict
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    # Only keep clusters with >= 2 members (single isolated reports are not clusters)
    significant_clusters = {root: members for root, members in clusters.items() if len(members) >= 2}
    logger.info(
        "GNN cluster sync: found %d significant clusters from %d reports",
        len(significant_clusters), n,
    )

    upserted = 0
    for root_idx, member_idxs in significant_clusters.items():
        member_reports = [reports[i] for i in member_idxs]
        member_entities = [report_entities[i] for i in member_idxs]

        # Collect signals
        bank_signals: list[str] = []
        phone_signals: list[str] = []
        domain_signals: list[str] = []
        categories: list[str] = []
        regions: list[str] = []

        for ent in member_entities:
            bank_signals.extend([f"{b[0]}:{b[1]}" for b in ent["banks"]])
            phone_signals.extend(ent["phones"])
            domain_signals.extend(ent["domains"])
            if ent["category"]:
                categories.append(ent["category"])

        for r in member_reports:
            if getattr(r, "city", None):
                regions.append(r.city)

        # Deduplicate
        bank_signals = list(dict.fromkeys(bank_signals))[:10]
        phone_signals = list(dict.fromkeys(phone_signals))[:10]
        domain_signals = list(dict.fromkeys(domain_signals))[:10]

        # Dominant category and region
        dominant_category = max(set(categories), key=categories.count) if categories else "Investasi Bodong"
        dominant_region = max(set(regions), key=regions.count) if regions else None

        # Risk level based on cluster size
        total = len(member_reports)
        if total >= 10:
            cluster_risk = "CRITICAL"
        elif total >= 5:
            cluster_risk = "HIGH"
        elif total >= 3:
            cluster_risk = "MEDIUM"
        else:
            cluster_risk = "LOW"

        # Matched signals for display
        matched_signals = bank_signals[:3] + phone_signals[:3] + domain_signals[:3]

        # Representative text from first member
        rep_report = member_reports[0]
        representative_text = (rep_report.rawInput or "")[:500]

        # Stable cluster ID based on root report ID (so upsert is idempotent)
        cluster_id = f"gnn_{rep_report.id}"
        group_name = f"{dominant_category} — Jaringan Terkait ({total} laporan)"

        try:
            # Upsert scam cluster record
            existing_cluster = await db.scamcluster.find_unique(where={"id": cluster_id})
            if existing_cluster:
                await db.scamcluster.update(
                    where={"id": cluster_id},
                    data={
                        "groupName": group_name,
                        "category": dominant_category,
                        "riskLevel": cluster_risk,
                        "totalReports": total,
                        "matchedSignals": matched_signals,
                        "bankAccounts": bank_signals,
                        "phoneNumbers": phone_signals,
                        "domains": domain_signals,
                        "dominantRegion": dominant_region,
                        "representativeText": representative_text,
                    },
                )
            else:
                await db.scamcluster.create(
                    data={
                        "id": cluster_id,
                        "groupName": group_name,
                        "category": dominant_category,
                        "riskLevel": cluster_risk,
                        "totalReports": total,
                        "matchedSignals": matched_signals,
                        "bankAccounts": bank_signals,
                        "phoneNumbers": phone_signals,
                        "domains": domain_signals,
                        "dominantRegion": dominant_region,
                        "representativeText": representative_text,
                    }
                )

            # Upsert ClusterMembership for each member report
            for r in member_reports:
                existing_membership = await db.clustermembership.find_first(
                    where={"clusterId": cluster_id, "reportId": r.id}
                )
                if not existing_membership:
                    await db.clustermembership.create(
                        data={
                            "clusterId": cluster_id,
                            "reportId": r.id,
                            "similarity": 1.0,  # All members in same component = fully connected
                        }
                    )

            upserted += 1

        except Exception as c_exc:
            logger.warning("Failed to upsert cluster %s: %s", cluster_id, c_exc)

    logger.info("✅ GNN cluster sync complete: %d clusters upserted to scam_clusters", upserted)
    return upserted



if __name__ == "__main__":
    asyncio.run(export_graph())
