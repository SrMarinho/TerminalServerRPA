from enum import Enum
from pathlib import Path
from typing import Any

import cv2
import numpy as np

cv2.setNumThreads(1)

_template_cache: dict[tuple[Path, float], Any] = {}


class MatchThreshold(float, Enum):
    FIELD = 0.75  # field image templates
    DEFAULT = 0.80  # window titles, error alert, coluna
    CHECKBOX = 0.90  # marked/unmarked checkbox states

    def __float__(self) -> float:
        return self.value


OCR_MIN_CONFIDENCE = 30


def _find_tesseract() -> str:
    import shutil

    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise RuntimeError("Tesseract não encontrado. Instale via: winget install UB-Mannheim.TesseractOCR")


def find_text(
    screenshot_bytes: bytes, text: str, lang: str = "por", return_text: bool = False
) -> bool | tuple[bool, str]:
    """Return True if text found in screenshot via OCR. If return_text=True, returns (found, ocr_text)."""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = _find_tesseract()
    img = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # type: ignore[arg-type]
    scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    result = pytesseract.image_to_string(binary, lang=lang)
    found = text.lower() in result.lower()
    if return_text:
        return found, result
    return found


def find_text_position(
    screenshot_bytes: bytes,
    *keywords: str,
    confidence: int = OCR_MIN_CONFIDENCE,
    scale: int = 2,
) -> tuple[int, int] | None:
    """Return center (x, y) of first word matching any keyword via OCR, else None."""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = _find_tesseract()
    raw = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR)
    if raw is None:
        return None
    up = cv2.resize(raw, (raw.shape[1] * scale, raw.shape[0] * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    data = pytesseract.image_to_data(thresh, lang="por", output_type=pytesseract.Output.DICT)
    for i, word in enumerate(data["text"]):
        w = word.strip().lower()
        if any(kw.lower() in w for kw in keywords) and int(data["conf"][i]) > confidence:
            cx = (data["left"][i] + data["width"][i] // 2) // scale
            cy = (data["top"][i] + data["height"][i] // 2) // scale
            return (cx, cy)
    return None


def _load_template(path: Path) -> Any:
    mtime = path.stat().st_mtime
    key = (path, mtime)
    if key not in _template_cache:
        needle = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if needle is None:
            raise FileNotFoundError(f"Template not found: {path}")
        _template_cache[key] = needle
        # Evict stale entries for the same path (different mtime)
        for k in [k for k in _template_cache if k[0] == path and k[1] != mtime]:
            del _template_cache[k]
    return _template_cache[key]


def find_template(
    screenshot_bytes: bytes,
    template_path: Path,
    confidence: float = MatchThreshold.DEFAULT,
) -> tuple[tuple[int, int], float] | None:
    """Return ((cx, cy), score) if template matched, None if below confidence."""
    haystack = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR)
    needle = _load_template(template_path)
    if needle is None:
        raise FileNotFoundError(f"Template not found: {template_path}")
    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)  # type: ignore[arg-type]
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < float(confidence):
        return None
    h, w = needle.shape[:2]
    return (max_loc[0] + w // 2, max_loc[1] + h // 2), max_val
