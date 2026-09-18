"""
Constants and configuration for GNN training/inference.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

GNN_MODEL_PATH = MODELS_DIR / "gnn_model.pt"
FEATURE_SCALER_PATH = MODELS_DIR / "feature_scaler.pkl"
TRAINING_LOG_PATH = MODELS_DIR / "training_log.json"
GRAPH_DATASET_PATH = MODELS_DIR / "gnn_dataset.pt"
GNN_METADATA_PATH = MODELS_DIR / "gnn_metadata.json"
TOPOLOGY_PATH = MODELS_DIR / "gnn_graph_topology.json"
VISUALIZATION_PLOT_PATH = MODELS_DIR / "training_visualization.png"


# ── Graph Schema ───────────────────────────────────────────────────────────
NODE_TYPES = [
    "Report",
    "BankAccount",
    "Phone",
    "Domain",
]

EDGE_TYPES = [
    ("Report", "mentions_account", "BankAccount"),
    ("Report", "mentions_phone", "Phone"),
    ("Report", "mentions_domain", "Domain"),
    ("BankAccount", "mentioned_in", "Report"),
    ("Phone", "mentioned_in", "Report"),
    ("Domain", "mentioned_in", "Report"),
    ("Report", "similar_content", "Report"),  # Text similarity > 0.6
    ("Report", "self_loop", "Report"),        # Self-propagation for text features
]

# ── Model Hyperparameters ───────────────────────────────────────────────────
HIDDEN_CHANNELS = 128
NUM_LAYERS = 2
DROPOUT_RATE = 0.3
LEARNING_RATE = 0.001
BATCH_SIZE = 32
EPOCHS = 100
PATIENCE = 10  # Early stopping
TEST_SPLIT = 0.15
VAL_SPLIT = 0.15
RANDOM_SEED = 42

# ── Feature Dimensions ──────────────────────────────────────────────────────
REPORT_FEAT_DIM = 64     # TF-IDF + categorical
ACCOUNT_FEAT_DIM = 8     # report_count, days_since_last_seen
PHONE_FEAT_DIM = 8
DOMAIN_FEAT_DIM = 8

# ── Training / Inference Toggles ────────────────────────────────────────────
# Default False to prevent OOM in Render Free Plan (512MB RAM).
# Can be enabled by setting ENABLE_GNN=true in environment or local development.
ENABLE_GNN = os.getenv("ENABLE_GNN", "false").lower() in ("true", "1", "yes")
GNN_FALLBACK_ON_ERROR = True
MAX_SUBGRAPH_NODES = 100
SIMILARITY_THRESHOLD = 0.6
