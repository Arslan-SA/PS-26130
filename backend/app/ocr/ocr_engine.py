"""
OCR Engine Integration — Pluggable Abstraction (Fragment 64).

Provides a unified OCR interface with three concrete adapters:
  - MockOCRAdapter       : Deterministic text responses for testing (default in dev)
  - TesseractOCRAdapter  : Local Tesseract 4.x integration (open-source, on-prem)
  - PaddleOCRAdapter     : PaddleOCR integration (high-accuracy for Indian documents)

The adapter is selected at startup from the OCR_ENGINE config setting.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("udyamsetu.ocr")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseOCRAdapter(ABC):
    """Abstract OCR engine contract."""

    @abstractmethod
    def extract_text(self, data: bytes, mime_type: str) -> str:
        """
        Extract raw text from raw file bytes.

        Args:
            data:      Raw file bytes (PDF, JPEG, PNG, etc.)
            mime_type: MIME type of the file.
        Returns:
            Extracted plain-text string (may be empty if unreadable).
        """


# ---------------------------------------------------------------------------
# Mock adapter (dev / CI)
# ---------------------------------------------------------------------------

class MockOCRAdapter(BaseOCRAdapter):
    """
    Returns deterministic, realistic mock text per MIME type.
    Used in development, CI, and test suites (zero external dependencies).
    """

    def extract_text(self, data: bytes, mime_type: str) -> str:
        logger.debug("MockOCRAdapter: generating synthetic OCR output for %s", mime_type)
        if "pdf" in mime_type:
            return (
                "GOVERNMENT OF INDIA\n"
                "PERMANENT ACCOUNT NUMBER CARD\n"
                "Name: RAJESH KUMAR PATEL\n"
                "Father's Name: RAMESH PATEL\n"
                "Date of Birth: 15/08/1982\n"
                "PAN: AAACB1234F\n"
                "Signature of the Income Tax Officer\n"
                "Income Tax Department, Ministry of Finance\n"
            )
        elif "image" in mime_type:
            return (
                "GSTIN: 27AAACB1234F1Z5\n"
                "Legal Name: BHARAT STEEL AND ALLOYS PRIVATE LIMITED\n"
                "Trade Name: BHARAT STEEL\n"
                "Registration Date: 14-07-2020\n"
                "State: Maharashtra\n"
                "Nature of Business: Manufacturer\n"
            )
        else:
            return (
                "CIN: U27100MH2020PTC345678\n"
                "Company Name: BHARAT STEEL AND ALLOYS PRIVATE LIMITED\n"
                "Date of Incorporation: 14/07/2020\n"
                "Registered Office: Plot No. E-42, MIDC Taloja, Raigad, Maharashtra 410208\n"
            )


# ---------------------------------------------------------------------------
# Tesseract adapter
# ---------------------------------------------------------------------------

class TesseractOCRAdapter(BaseOCRAdapter):
    """
    Integrates with system-installed Tesseract 4.x for on-premise OCR.
    Requires: `pip install pytesseract Pillow pdf2image`
    """

    def __init__(self) -> None:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore  # noqa: F401
            self._pytesseract = pytesseract
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            logger.info("TesseractOCRAdapter initialised.")
        except ImportError as exc:
            raise RuntimeError(
                "Tesseract OCR requires pytesseract and Pillow: "
                "`pip install pytesseract Pillow pdf2image`"
            ) from exc

    def extract_text(self, data: bytes, mime_type: str) -> str:
        import io
        from PIL import Image  # type: ignore

        if "pdf" in mime_type:
            # PDF → images → OCR each page
            try:
                from pdf2image import convert_from_bytes  # type: ignore
                images = convert_from_bytes(data, dpi=200)
                texts = [self._pytesseract.image_to_string(img, lang="eng+hin") for img in images]
                return "\n".join(texts)
            except Exception as exc:  # noqa: BLE001
                logger.warning("PDF OCR failed: %s", exc)
                return ""
        else:
            try:
                img = Image.open(io.BytesIO(data))
                return self._pytesseract.image_to_string(img, lang="eng+hin")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Image OCR failed: %s", exc)
                return ""


# ---------------------------------------------------------------------------
# PaddleOCR adapter (stub — high-accuracy model for prod)
# ---------------------------------------------------------------------------

class PaddleOCRAdapter(BaseOCRAdapter):
    """
    PaddleOCR integration for high-accuracy multi-language document processing.
    Requires: `pip install paddleocr paddlepaddle`
    """

    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore
            self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            logger.info("PaddleOCRAdapter initialised.")
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR requires paddleocr and paddlepaddle: "
                "`pip install paddleocr paddlepaddle`"
            ) from exc

    def extract_text(self, data: bytes, mime_type: str) -> str:
        import io
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore

        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            result = self._ocr.ocr(np.array(img), cls=True)
            lines = []
            for block in result or []:
                for line in block or []:
                    if line and len(line) >= 2:
                        lines.append(str(line[1][0]))
            return "\n".join(lines)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PaddleOCR failed: %s", exc)
            return ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_ocr_adapter() -> BaseOCRAdapter:
    """
    Factory: return the configured OCR adapter based on OCR_ENGINE setting.
    Falls back to MockOCRAdapter if engine not recognised.
    """
    engine = settings.OCR_ENGINE.lower()
    if engine == "tesseract":
        return TesseractOCRAdapter()
    if engine == "paddleocr":
        return PaddleOCRAdapter()
    logger.info("OCR engine: mock (set OCR_ENGINE=tesseract or paddleocr for production)")
    return MockOCRAdapter()
