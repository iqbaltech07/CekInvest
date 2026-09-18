"""
GNN Inference Service — robust, production-ready inference.
All heavy imports (torch, torch_geometric) are lazy — importing this module never fails
when ML dependencies are missing. The API gracefully degrades to no GNN boost.
"""
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GNNService:
    _instance = None
    _model = None
    _device = None
    _vectorizer = None
    _metadata = None
    _available = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GNNService, cls).__new__(cls)
        return cls._instance

    # ── Availability ────────────────────────────────────────────────────────
    @property
    def is_available(self) -> bool:
        """True once the model has been successfully loaded."""
        return self._available

    def _import_ml(self) -> bool:
        """
        Lazily import torch + torch_geometric and constants.
        Returns False (graceful) when ML deps are missing.
        """
        try:
            import torch  # noqa: F401
            from torch_geometric.data import HeteroData  # noqa: F401
        except ImportError:
            logger.warning("PyTorch / PyG not installed — GNN boost disabled.")
            return False

        try:
            from ml import constants  # noqa: F401
        except ImportError:
            logger.warning("ml.constants not importable — GNN boost disabled.")
            return False
        return True

    # ── Model Loading ───────────────────────────────────────────────────────
    def load_model(self) -> bool:
        """Lazy load the GNN model, metadata, and fitted TF-IDF vectorizer."""
        from ml import constants as C
        if not C.ENABLE_GNN:
            logger.info("ℹ️ GNN boost disabled via ENABLE_GNN=false (Render Free Plan / Low RAM mode).")
            return False

        if self._available and self._model is not None:
            return True

        if not self._import_ml():
            return False

        import torch

        if not C.GNN_MODEL_PATH.exists():
            logger.warning(
                "GNN model checkpoint not found at %s. GNN boost disabled.",
                C.GNN_MODEL_PATH,
            )
            return False

        try:
            # 1. TF-IDF vectorizer (pre-fitted during export)
            if C.MODELS_DIR.joinpath("tfidf_vectorizer.pkl").exists():
                with open(C.MODELS_DIR.joinpath("tfidf_vectorizer.pkl"), "rb") as f:
                    self._vectorizer = pickle.load(f)
                logger.info("Pre-fitted TF-IDF vectorizer loaded.")
            else:
                logger.warning("Pre-fitted vectorizer missing — feature extraction degraded.")

            # 2. Metadata (node/edge types) — persisted during export
            meta_path = C.MODELS_DIR / "gnn_metadata.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self._metadata = (meta["node_types"], [tuple(e) for e in meta["edge_types"]])
            else:
                self._metadata = (
                    ["Report", "BankAccount", "Phone", "Domain"],
                    [
                        ("Report", "mentions_account", "BankAccount"),
                        ("Report", "mentions_phone", "Phone"),
                        ("Report", "mentions_domain", "Domain"),
                        ("Report", "similar_content", "Report"),
                    ],
                )

            # 3. Model — lazy import of training module (avoids heavy import at boot)
            from ml.train_sage import HeteroGraphSAGE

            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            self._model = HeteroGraphSAGE(
                metadata=self._metadata,
                hidden_channels=C.HIDDEN_CHANNELS,
                out_channels=1,
                num_layers=C.NUM_LAYERS,
            )
            self._model.load_state_dict(
                torch.load(C.GNN_MODEL_PATH, map_location=self._device)
            )
            self._model.to(self._device)
            self._model.eval()

            self._available = True
            logger.info("GNN model loaded successfully on %s", self._device)
            return True
        except FileNotFoundError as exc:
            logger.error("GNN artifact missing: %s", exc)
            return False
        except Exception as exc:
            logger.error("Failed to load GNN artifacts: %s", exc, exc_info=True)
            return False

    # ── Inference ───────────────────────────────────────────────────────────
    async def get_risk_boost(
        self,
        text: str,
        category: str | None = None,
        db: Any = None,
    ) -> float:
        """
        Compute GNN risk boost for new input text.
        Guaranteed safe: catches any anomaly and returns 0.0 without throwing.
        """
        try:
            from ml import constants as C
            if not C.ENABLE_GNN:
                return 0.0

            if not self.load_model():
                return 0.0
            import numpy as np
            import torch
            from torch_geometric.data import HeteroData

            from ml import constants as C
            from ml.utils import (
                extract_phone_numbers,
                extract_bank_accounts,
                extract_domains,
                normalize_text,
            )

            phones = extract_phone_numbers(text)
            banks = extract_bank_accounts(text)
            domains = extract_domains(text)

            # Feature extraction for Report node using pre-fitted vectorizer
            norm_text = normalize_text(text)
            if self._vectorizer is not None:
                try:
                    feat_array = self._vectorizer.transform([norm_text]).toarray()[0]
                except Exception as exc:
                    logger.debug("Vectorizer transform failed: %s", exc)
                    feat_array = np.zeros(C.REPORT_FEAT_DIM)
            else:
                feat_array = np.zeros(C.REPORT_FEAT_DIM)

            report_x = torch.from_numpy(feat_array).float().unsqueeze(0)

            # Build a subgraph connecting Report node to extracted entities
            data = HeteroData()
            data["Report"].x = report_x

            # Entity feature tensors
            x_banks = np.zeros((max(1, len(banks)), C.ACCOUNT_FEAT_DIM))
            x_phones = np.zeros((max(1, len(phones)), C.PHONE_FEAT_DIM))
            x_domains = np.zeros((max(1, len(domains)), C.DOMAIN_FEAT_DIM))

            # Query community DB for known scam counts if DB is provided
            if db is not None:
                for idx, (b_name, b_acct) in enumerate(banks):
                    try:
                        rec = await db.bankaccountreport.find_unique(
                            where={"bankName_accountNumber": {"bankName": b_name, "accountNumber": b_acct}}
                        )
                        if rec:
                            x_banks[idx, 0] = min(rec.reportCount / 100.0, 1.0)
                    except Exception:
                        pass

                for idx, p_num in enumerate(phones):
                    try:
                        rec = await db.phonereport.find_unique(where={"phoneNumber": p_num})
                        if rec:
                            x_phones[idx, 0] = min(rec.reportCount / 100.0, 1.0)
                    except Exception:
                        pass

            data["BankAccount"].x = torch.from_numpy(x_banks).float()
            data["Phone"].x = torch.from_numpy(x_phones).float()
            data["Domain"].x = torch.from_numpy(x_domains).float()

            empty_edge = torch.empty((2, 0), dtype=torch.long)
            if banks:
                data["Report", "mentions_account", "BankAccount"].edge_index = torch.tensor(
                    [[0] * len(banks), list(range(len(banks)))], dtype=torch.long
                )
            else:
                data["Report", "mentions_account", "BankAccount"].edge_index = empty_edge

            if phones:
                data["Report", "mentions_phone", "Phone"].edge_index = torch.tensor(
                    [[0] * len(phones), list(range(len(phones)))], dtype=torch.long
                )
            else:
                data["Report", "mentions_phone", "Phone"].edge_index = empty_edge

            if domains:
                data["Report", "mentions_domain", "Domain"].edge_index = torch.tensor(
                    [[0] * len(domains), list(range(len(domains)))], dtype=torch.long
                )
            else:
                data["Report", "mentions_domain", "Domain"].edge_index = empty_edge

            # Incoming edges from entities into Report
            if banks:
                data["BankAccount", "mentioned_in", "Report"].edge_index = torch.tensor(
                    [list(range(len(banks))), [0] * len(banks)], dtype=torch.long
                )
            else:
                data["BankAccount", "mentioned_in", "Report"].edge_index = empty_edge

            if phones:
                data["Phone", "mentioned_in", "Report"].edge_index = torch.tensor(
                    [list(range(len(phones))), [0] * len(phones)], dtype=torch.long
                )
            else:
                data["Phone", "mentioned_in", "Report"].edge_index = empty_edge

            if domains:
                data["Domain", "mentioned_in", "Report"].edge_index = torch.tensor(
                    [list(range(len(domains))), [0] * len(domains)], dtype=torch.long
                )
            else:
                data["Domain", "mentioned_in", "Report"].edge_index = empty_edge

            data["Report", "similar_content", "Report"].edge_index = empty_edge
            data["Report", "self_loop", "Report"].edge_index = torch.tensor([[0], [0]], dtype=torch.long)

            data = data.to(self._device)
            with torch.no_grad():
                out = self._model(data.x_dict, data.edge_index_dict)
                prob = float(torch.sigmoid(out).item())

            # Isolated node (no entities) must not produce a phantom boost
            if not phones and not banks and not domains:
                logger.debug("GNN: fully isolated node — no boost.")
                return 0.0

            # Only boost if probability exceeds scam classification threshold (0.5)
            if prob <= 0.5:
                logger.debug("GNN: probability below scam threshold (%.4f <= 0.5) — no boost.", prob)
                return 0.0

            boost = round(min(25.0, (prob - 0.5) * 2.0 * 25.0), 1)
            logger.info("GNN inference: prob=%.4f, boost=+%.1f", prob, boost)
            return boost
        except Exception as exc:
            logger.warning("GNN inference failed, bypassing boost: %s", exc)
            return 0.0


# Singleton — safe to import even without ML deps
gnn_service = GNNService()
