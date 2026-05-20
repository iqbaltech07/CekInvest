"""
OCR service — extracts text from uploaded screenshot images using pytesseract.
"""
import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

# Lazy import to avoid error if tesseract is not installed
try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed. Screenshot OCR will be unavailable.")


async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, WEBP, etc.)

    Returns:
        Extracted text string (may be empty if no text found).

    Raises:
        ValueError: If the image cannot be processed.
    """
    if not _TESSERACT_AVAILABLE:
        raise ValueError(
            "OCR service is unavailable. Please install Tesseract and pytesseract."
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Improve OCR accuracy for Indonesian + English text
        custom_config = r"--oem 3 --psm 6 -l ind+eng"
        text: str = pytesseract.image_to_string(image, config=custom_config)

        cleaned = text.strip()
        logger.debug("OCR extracted %d characters from image", len(cleaned))
        return cleaned

    except Exception as exc:
        logger.exception("OCR extraction failed: %s", exc)
        raise ValueError(f"Failed to extract text from image: {exc}") from exc


def is_ocr_available() -> bool:
    """Check whether Tesseract OCR is available on this system."""
    return _TESSERACT_AVAILABLE
