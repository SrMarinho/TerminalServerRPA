from pathlib import Path

import cv2
import numpy as np


def _find_tesseract() -> str:
    import shutil
    from pathlib import Path

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


def find_template(
    screenshot_bytes: bytes,
    template_path: Path,
    confidence: float = 0.8,
) -> tuple[tuple[int, int], float] | None:
    """Return ((cx, cy), score) if template matched, None if below confidence."""
    haystack = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR)
    needle = cv2.imdecode(np.fromfile(str(template_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if needle is None:
        raise FileNotFoundError(f"Template not found: {template_path}")
    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)  # type: ignore[arg-type]
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < confidence:
        return None
    h, w = needle.shape[:2]
    return (max_loc[0] + w // 2, max_loc[1] + h // 2), max_val
