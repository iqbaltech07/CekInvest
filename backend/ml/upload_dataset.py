"""
Standalone CLI script to upload/import dataset files (CSV or JSON) into CekInvest GNN.
Run: python -m ml.upload_dataset path/to/dataset.csv
"""
import argparse
import asyncio
import csv
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from prisma import Prisma
from ml.export_graph import export_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def import_file(file_path: Path):
    if not file_path.exists():
        logger.error("File tidak ditemukan: %s", file_path)
        sys.exit(1)

    print("\n" + "=" * 68)
    print(" >>> CEKINVEST DATASET INGESTION TOOL <<<")
    print("=" * 68)
    print(f" Reading: {file_path}")

    records = []
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                text = norm_row.get("text") or norm_row.get("rawinput") or norm_row.get("pesan")
                if not text:
                    continue

                val_scam = norm_row.get("is_scam", norm_row.get("isscam", norm_row.get("scam", norm_row.get("label", "0"))))
                is_scam = str(val_scam).lower() in ("1", "true", "yes", "ya", "t", "scam")
                category = norm_row.get("category") or norm_row.get("scamcategory") or ("Investasi Bodong" if is_scam else "Legal")

                records.append({
                    "rawInput": text,
                    "inputType": "CHAT",
                    "isScam": is_scam,
                    "scamCategory": category,
                    "bankName": norm_row.get("bank_name") or norm_row.get("bankname") or None,
                    "bankAccount": norm_row.get("bank_account") or norm_row.get("bankaccount") or None,
                    "phoneNumber": norm_row.get("phone") or norm_row.get("phonenumber") or None,
                    "domain": norm_row.get("domain") or None,
                })

    elif suffix == ".json":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
            raw_list = data if isinstance(data, list) else data.get("data", [])
            for item in raw_list:
                norm_item = {str(k).strip().lower(): str(v).strip() for k, v in item.items() if k}
                text = norm_item.get("text") or norm_item.get("rawinput") or norm_item.get("pesan")
                if not text:
                    continue

                val_scam = norm_item.get("is_scam", norm_item.get("isscam", norm_item.get("scam", norm_item.get("label", "0"))))
                is_scam = str(val_scam).lower() in ("1", "true", "yes", "ya", "t", "scam")
                category = norm_item.get("category") or norm_item.get("scamcategory") or ("Investasi Bodong" if is_scam else "Legal")

                records.append({
                    "rawInput": text,
                    "inputType": "CHAT",
                    "isScam": is_scam,
                    "scamCategory": category,
                    "bankName": norm_item.get("bank_name") or norm_item.get("bankname") or None,
                    "bankAccount": norm_item.get("bank_account") or norm_item.get("bankaccount") or None,
                    "phoneNumber": norm_item.get("phone") or norm_item.get("phonenumber") or None,
                    "domain": norm_item.get("domain") or None,
                })

    else:
        logger.error("Format tidak didukung. Harap gunakan file .csv atau .json")
        sys.exit(1)

    if not records:
        logger.error("Tidak ada data valid yang dapat diimpor (kolom 'text' atau 'rawInput' kosong).")
        sys.exit(1)

    print(f" Parsed {len(records)} valid records. Inserting to database...")
    db = Prisma()
    await db.connect()

    inserted = 0
    for r in records:
        await db.userreport.create(data=r)
        inserted += 1

    total_in_db = await db.userreport.count()
    await db.disconnect()

    print(f" [OK] Successfully inserted {inserted} records. Total UserReports in DB: {total_in_db}")
    print(" Synchronizing GNN PyG HeteroData graph and visual topology...")
    await export_graph()
    print(" [OK] GNN Graph dataset & visual topology synchronized successfully!")
    print("=" * 68)
    print(" Siap dilatih ulang! Jalankan 'python -m ml.train_sage' atau buka Web Dashboard.")
    print("=" * 68 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Import dataset CSV/JSON into CekInvest GNN")
    parser.add_argument("file", type=str, help="Path to CSV or JSON dataset file")
    args = parser.parse_args()

    asyncio.run(import_file(Path(args.file)))


if __name__ == "__main__":
    main()
