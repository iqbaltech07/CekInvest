"""
HeteroGraphSAGE training script — train a GNN for scam node classification.
Run: python -m ml.train_sage

Handles edge cases:
  - Missing dataset
  - Insufficient samples
  - Single-class labels
"""
import json
import logging
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv, Linear

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.constants import (
    GRAPH_DATASET_PATH,
    GNN_MODEL_PATH,
    TRAINING_LOG_PATH,
    VISUALIZATION_PLOT_PATH,
    HIDDEN_CHANNELS,
    NUM_LAYERS,
    LEARNING_RATE,
    EPOCHS,
    RANDOM_SEED,
    TEST_SPLIT,
    VAL_SPLIT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

MIN_SAMPLES = 10


# ── Model Definition ────────────────────────────────────────────────────────

class HeteroGraphSAGE(torch.nn.Module):
    def __init__(self, metadata, hidden_channels, out_channels, num_layers):
        super().__init__()
        
        self.convs = torch.nn.ModuleList()
        for i in range(num_layers):
            conv = HeteroConv({
                edge_type: SAGEConv((-1, -1), hidden_channels)
                for edge_type in metadata[1]
            }, aggr="sum")
            self.convs.append(conv)
            
        self.lin = Linear(hidden_channels, out_channels)

    def forward(self, x_dict, edge_index_dict):
        for conv in self.convs:
            x_dict = conv(x_dict, edge_index_dict)
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}
            x_dict = {key: F.dropout(x, p=0.3, training=self.training) for key, x in x_dict.items()}
            
        return self.lin(x_dict["Report"])


# ── Training Generator & Script ─────────────────────────────────────────────

def train_generator(
    epochs: int = EPOCHS,
    lr: float = LEARNING_RATE,
    test_split: float = TEST_SPLIT,
    val_split: float = VAL_SPLIT,
    live_plot: bool = False,
):
    """
    Generator yielding real-time training progress dictionary per epoch.
    Enables live streaming over Server-Sent Events (SSE), WebSockets, or UI dashboards.
    Data split is dynamically computed based on current dataset size using round().
    """
    if not GRAPH_DATASET_PATH.exists():
        logger.error("Dataset not found at %s. Run ml/export_graph.py first.", GRAPH_DATASET_PATH)
        yield {"event": "error", "message": f"Dataset not found at {GRAPH_DATASET_PATH}"}
        return

    logger.info("Loading graph dataset...")
    data = torch.load(GRAPH_DATASET_PATH, weights_only=False)
    
    # ── Validate dataset ────────────────────────────────────────────────────
    num_reports = data["Report"].num_nodes
    if num_reports < MIN_SAMPLES:
        msg = f"Insufficient data: {num_reports} reports (need >= {MIN_SAMPLES})."
        logger.error(msg)
        yield {"event": "error", "message": msg}
        return
    
    labels = data["Report"].y
    unique_labels = torch.unique(labels)
    if len(unique_labels) < 2:
        msg = f"Single-class labels detected: {unique_labels.tolist()}. Need both scam and non-scam reports."
        logger.error(msg)
        yield {"event": "error", "message": msg}
        return
    
    logger.info("Dataset validated: %d reports, labels=%s", num_reports, unique_labels.tolist())
    
    # ── Split data dynamically ───────────────────────────────────────────────
    torch.manual_seed(RANDOM_SEED)
    indices = torch.randperm(num_reports)
    
    val_size = max(1, round(num_reports * val_split))
    test_size = max(1, round(num_reports * test_split))
    train_size = num_reports - val_size - test_size
    
    if train_size <= 0:
        yield {"event": "error", "message": "Not enough samples for training after split."}
        return
    
    train_idx = indices[:train_size]
    val_idx = indices[train_size:train_size + val_size]
    test_idx = indices[train_size + val_size:]
    
    train_mask = torch.zeros(num_reports, dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask = torch.zeros(num_reports, dtype=torch.bool)
    val_mask[val_idx] = True
    test_mask = torch.zeros(num_reports, dtype=torch.bool)
    test_mask[test_idx] = True
    
    data["Report"].train_mask = train_mask
    data["Report"].val_mask = val_mask
    data["Report"].test_mask = test_mask
    
    yield {
        "event": "start",
        "total_epochs": epochs,
        "num_reports": num_reports,
        "train_size": train_size,
        "val_size": val_size,
        "test_size": test_size,
    }
    
    # ── Initialize model ────────────────────────────────────────────────────
    model = HeteroGraphSAGE(
        metadata=data.metadata(),
        hidden_channels=HIDDEN_CHANNELS,
        out_channels=1,
        num_layers=NUM_LAYERS,
    )
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    data = data.to(device)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.BCEWithLogitsLoss()
    
    best_val_loss = float("inf")
    best_state_dict = None
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": [], "test_acc": 0.0}
    
    # Live Matplotlib setup if requested
    live_fig, live_ax = None, None
    line_train, line_val = None, None
    if live_plot:
        try:
            import matplotlib.pyplot as plt
            plt.ion()
            live_fig, live_ax = plt.subplots(figsize=(9, 5))
            live_fig.patch.set_facecolor("#0B0F19")
            live_ax.set_facecolor("#111827")
            live_ax.set_title("CekInvest GNN — Real-time Training Convergence", color="#F8FAFC", fontsize=12, fontweight="bold")
            live_ax.set_xlabel("Epoch", color="#94A3B8")
            live_ax.set_ylabel("BCE Loss", color="#94A3B8")
            live_ax.grid(True, linestyle=":", alpha=0.3, color="#64748B")
            (line_train,) = live_ax.plot([], [], label="Train Loss", color="#EF4444", linewidth=2.0)
            (line_val,) = live_ax.plot([], [], label="Val Loss", color="#38BDF8", linewidth=2.0, linestyle="--")
            live_ax.legend(facecolor="#1F2937", edgecolor="#374151")
            plt.tight_layout()
            plt.show(block=False)
        except Exception as exc:
            logger.warning("Could not initialize live GUI plot: %s", exc)
            live_plot = False

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        
        out = model(data.x_dict, data.edge_index_dict).squeeze()
        loss = criterion(out[data["Report"].train_mask], data["Report"].y[data["Report"].train_mask].float())
        
        loss.backward()
        optimizer.step()
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_out = model(data.x_dict, data.edge_index_dict).squeeze()
            val_loss = criterion(val_out[data["Report"].val_mask], data["Report"].y[data["Report"].val_mask].float())
            
            # Compute accuracy
            train_pred = (out[data["Report"].train_mask] > 0).long()
            train_acc = float((train_pred == data["Report"].y[data["Report"].train_mask]).sum() / data["Report"].train_mask.sum())
            
            val_pred = (val_out[data["Report"].val_mask] > 0).long()
            val_acc = float((val_pred == data["Report"].y[data["Report"].val_mask]).sum() / data["Report"].val_mask.sum())
            
        t_loss = float(loss.detach().cpu())
        v_loss = float(val_loss.detach().cpu())
        history["train_loss"].append(t_loss)
        history["val_loss"].append(v_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)
        
        is_new_best = v_loss < best_val_loss
        if is_new_best:
            best_val_loss = v_loss
            best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # Live plot update
        if live_plot and live_fig and live_ax:
            try:
                import matplotlib.pyplot as plt
                epochs_range = list(range(1, epoch + 1))
                line_train.set_data(epochs_range, history["train_loss"])
                line_val.set_data(epochs_range, history["val_loss"])
                live_ax.relim()
                live_ax.autoscale_view()
                live_fig.canvas.draw()
                live_fig.canvas.flush_events()
                plt.pause(0.01)
            except Exception:
                pass

        yield {
            "event": "epoch",
            "epoch": epoch,
            "total_epochs": epochs,
            "train_loss": round(t_loss, 5),
            "val_loss": round(v_loss, 5),
            "train_acc": round(train_acc, 4),
            "val_acc": round(val_acc, 4),
            "best_val": round(best_val_loss, 5),
            "is_best": is_new_best,
        }
            
    # ── Final evaluation ────────────────────────────────────────────────────
    if best_state_dict is not None:
        torch.save(best_state_dict, GNN_MODEL_PATH)
        model.load_state_dict(best_state_dict)
    
    model.eval()
    with torch.no_grad():
        out = model(data.x_dict, data.edge_index_dict).squeeze()
        pred = (out > 0).long()
        correct = (pred[data["Report"].test_mask] == data["Report"].y[data["Report"].test_mask]).sum()
        acc = float(int(correct) / int(data["Report"].test_mask.sum()))
        
    history["test_acc"] = acc
    
    # Save training logs
    TRAINING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRAINING_LOG_PATH, "w") as f:
        json.dump(history, f, indent=2)
        
    logger.info("Training complete. Model saved to %s", GNN_MODEL_PATH)

    # ── Save Visual Chart ───────────────────────────────────────────────────
    _generate_training_plot(history, data, out, VISUALIZATION_PLOT_PATH)

    if live_plot and live_fig:
        try:
            import matplotlib.pyplot as plt
            plt.ioff()
            plt.close(live_fig)
        except Exception:
            pass

    yield {
        "event": "done",
        "test_acc": round(acc, 4),
        "best_val_loss": round(best_val_loss, 5),
        "total_epochs": epochs,
        "model_path": str(GNN_MODEL_PATH),
        "plot_path": str(VISUALIZATION_PLOT_PATH),
    }


def train(epochs: int = EPOCHS, lr: float = LEARNING_RATE, live_plot: bool = False) -> bool:
    """Synchronous wrapper for train_generator with ASCII terminal monitor."""
    print("\n" + "=" * 68)
    print(" >>> HETEROGRAPHSAGE GNN TRAINING MONITOR <<<")
    print("=" * 68)

    generator = train_generator(epochs=epochs, lr=lr, live_plot=live_plot)
    success = False

    for event in generator:
        if event.get("event") == "error":
            logger.error("Training error: %s", event.get("message"))
            return False
        elif event.get("event") == "start":
            print(f" Dataset : {event['num_reports']} Reports | Split: Train={event['train_size']}, Val={event['val_size']}, Test={event['test_size']}")
            print("-" * 68)
        elif event.get("event") == "epoch":
            epoch = event["epoch"]
            total = event["total_epochs"]
            t_loss = event["train_loss"]
            v_loss = event["val_loss"]
            t_acc = event["train_acc"]
            v_acc = event["val_acc"]
            is_best = event["is_best"]

            bar_len = 18
            filled = int(bar_len * epoch / total)
            bar = "#" * filled + "-" * (bar_len - filled)
            best_star = " * [BEST]" if is_best else "         "
            sys.stdout.write(
                f"\rEpoch [{epoch:03d}/{total:03d}] [{bar}] Loss: {t_loss:.4f} (Val: {v_loss:.4f}) | Acc: {t_acc*100:.0f}%/{v_acc*100:.0f}%{best_star}"
            )
            sys.stdout.flush()
            if epoch % 10 == 0 or epoch == total:
                print()
        elif event.get("event") == "done":
            success = True
            print("\n" + "=" * 68)
            print(f" [OK] TRAINING COMPLETE: Test Acc = {event['test_acc'] * 100:.1f}% | Best Val Loss = {event['best_val_loss']:.4f}")
            print(f" [OK] Model saved to {event['model_path']}")
            print(f" [OK] Plot saved to {event['plot_path']}")
            print("=" * 68 + "\n")

    return success


def _generate_training_plot(history: dict, data: HeteroData, out: torch.Tensor, save_path: Path) -> None:
    """Generate high-resolution training loss and accuracy visualization chart."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.style.use("dark_background")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig.patch.set_facecolor("#0B0F19")
        ax1.set_facecolor("#111827")
        ax2.set_facecolor("#111827")

        epochs = range(1, len(history["train_loss"]) + 1)
        ax1.plot(epochs, history["train_loss"], label="Train Loss", color="#EF4444", linewidth=2.2)
        ax1.plot(epochs, history["val_loss"], label="Val Loss", color="#38BDF8", linewidth=2.2, linestyle="--")

        min_val = min(history["val_loss"])
        best_epoch = history["val_loss"].index(min_val) + 1
        ax1.scatter([best_epoch], [min_val], color="#10B981", s=120, zorder=5, label=f"Best Val ({min_val:.4f} @ ep {best_epoch})")

        ax1.set_title("HeteroGraphSAGE — Loss Curve", fontsize=12, fontweight="bold", color="#F8FAFC", pad=12)
        ax1.set_xlabel("Epoch", fontsize=10, color="#94A3B8")
        ax1.set_ylabel("BCEWithLogitsLoss", fontsize=10, color="#94A3B8")
        ax1.grid(True, linestyle=":", alpha=0.3, color="#64748B")
        ax1.legend(loc="upper right", facecolor="#1F2937", edgecolor="#374151")

        # Subplot 2: Test Split Prediction Distribution
        test_mask = data["Report"].test_mask.cpu()
        y_test = data["Report"].y[test_mask].cpu().numpy()
        probs_test = torch.sigmoid(out[test_mask]).detach().cpu().numpy()

        ax2.hist(
            [probs_test[y_test == 0], probs_test[y_test == 1]],
            bins=10,
            label=["Legitimate (y=0)", "Scam (y=1)"],
            color=["#10B981", "#EF4444"],
            rwidth=0.8,
            alpha=0.9,
        )
        ax2.set_title(
            f"Test Split Prediction Confidence (Acc: {history['test_acc']*100:.1f}%)",
            fontsize=12,
            fontweight="bold",
            color="#F8FAFC",
            pad=12,
        )
        ax2.set_xlabel("Predicted Scam Probability", fontsize=10, color="#94A3B8")
        ax2.set_ylabel("Count", fontsize=10, color="#94A3B8")
        ax2.grid(True, linestyle=":", alpha=0.3, color="#64748B")
        ax2.legend(loc="upper center", facecolor="#1F2937", edgecolor="#374151")

        plt.tight_layout()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=160, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close()
        logger.info("[OK] Visual plot chart saved to %s", save_path)
    except Exception as exc:
        logger.warning("Could not generate visual chart: %s", exc)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train CekInvest HeteroGraphSAGE GNN")
    parser.add_argument("--epochs", type=int, default=EPOCHS, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE, help="Learning rate")
    parser.add_argument("--live", action="store_true", help="Display live Matplotlib training plot window")
    args = parser.parse_args()

    success = train(epochs=args.epochs, lr=args.lr, live_plot=args.live)
    sys.exit(0 if success else 1)


