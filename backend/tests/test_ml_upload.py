"""
Tests for ML Dataset Upload and Retraining pipeline.
"""
import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_download_dataset_template(client: AsyncClient):
    """Verify that user can download the dataset CSV template."""
    response = await client.get("/api/v1/ml/download-template")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    content = response.text
    assert "rawInput" in content or "text" in content
    assert "is_scam" in content or "isScam" in content


@pytest.mark.asyncio
async def test_upload_dataset_invalid_extension(client: AsyncClient):
    """Verify that uploading non-csv/json files is rejected with 400."""
    files = {"file": ("test.txt", b"some text content", "text/plain")}
    response = await client.post("/api/v1/ml/upload-dataset", files=files)
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_upload_dataset_empty_data(client: AsyncClient):
    """Verify that uploading CSV without text rows is rejected with 400."""
    csv_content = "text,is_scam\n,"
    files = {"file": ("empty.csv", csv_content.encode("utf-8"), "text/csv")}
    response = await client.post("/api/v1/ml/upload-dataset", files=files)
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_upload_dataset_valid_csv(client: AsyncClient):
    """Verify that uploading valid CSV inserts data and returns updated total."""
    csv_content = (
        "text,is_scam,category,bank_name,bank_account,phone,domain\n"
        '"Test investasi bodong bunga 50% transfer BCA 9911223344 hub 081288776655 web c-test.xyz",1,"Investasi Bodong","BCA","9911223344","081288776655","c-test.xyz"\n'
        '"Pengumuman rapat umum pemegang saham tahunan PT Astra International Tbk resmi OJK",0,"Legal","","","","astra.co.id"\n'
    )
    files = {"file": ("test_upload.csv", csv_content.encode("utf-8"), "text/csv")}
    response = await client.post("/api/v1/ml/upload-dataset", files=files, timeout=30.0)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["inserted_count"] == 2
    assert data["data"]["total_reports"] > 111
