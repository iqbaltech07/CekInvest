"""
Standalone CLI launcher for CekInvest GNN Interactive Visualizer.
Run: python -m ml.visualizer
"""
import sys
import webbrowser
from pathlib import Path

import uvicorn

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def main():
    port = 8000
    url = f"http://localhost:{port}/api/v1/ml/dashboard"
    print("\n" + "=" * 68)
    print(" >>> CEKINVEST GNN INTERACTIVE TRAINING VISUALIZER <<<")
    print("=" * 68)
    print(f" * Dashboard URL: {url}")
    print(" * Opening browser automatically...")
    print("=" * 68 + "\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
