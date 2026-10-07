import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfReader


def load_catalog(root):
    return json.loads((Path(root) / "catalog.json").read_text(encoding="utf-8"))


def source_bytes(root, spec):
    root = Path(root).resolve()
    path = (root / spec["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Source path leaves the collection.")
    with path.open("rb") as source:
        raw = source.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Source exceeds this recipe's size limit.")
    return path, raw


def extract(root, spec):
    path, raw = source_bytes(root, spec)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        units = [("text", raw.decode("utf-8"))]
    elif suffix == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF requires separate handling.")
        units = [(f"page {n}", page.extract_text() or "")
                 for n, page in enumerate(reader.pages, 1)]
    else:
        raise ValueError("Unsupported document format.")
    if not units or any(not text.strip() for _, text in units):
        raise ValueError("Empty extraction requires inspection.")
    return hashlib.sha256(raw).hexdigest(), units
