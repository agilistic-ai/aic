import hashlib
import io
import shutil
import wave
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
from pypdf import PdfReader


def limited_bytes(path, limit):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Media exceeds this recipe's size limit.")
    return raw


def prepare(visual_path, audio_path, *, consent, output="runs/media"):
    if consent is not True:
        raise PermissionError("Recording and processing consent is required.")
    folder = Path(output).resolve() / uuid4().hex
    folder.mkdir(parents=True)
    try:
        raw = limited_bytes(visual_path, 10_000_000)
        if Path(visual_path).suffix.lower() == ".pdf":
            pdf = PdfReader(io.BytesIO(raw))
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 5:
                raise ValueError("Supply an unencrypted PDF of one to five pages.")
            visual = folder / "source.pdf"
            visual.write_bytes(raw)
            pages, kind = len(pdf.pages), "pdf"
        else:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"PNG", "JPEG"} or image.width * image.height > 20_000_000:
                    raise ValueError("Supply a PNG or JPEG within the pixel limit.")
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                normalized.info.clear()
                visual = folder / "source.png"
                normalized.save(visual)
            pages, kind = 1, "image"
        if visual.stat().st_size > 20_000_000:
            raise ValueError("Working image is too large; supply a focused crop.")
        audio_raw = limited_bytes(audio_path, 10_000_000)
        with wave.open(io.BytesIO(audio_raw), "rb") as recording:
            channels, width, rate, frames = (recording.getnchannels(), recording.getsampwidth(),
                                             recording.getframerate(), recording.getnframes())
            if channels not in {1, 2} or width != 2 or not 16000 <= rate <= 48000:
                raise ValueError("Supply 16-bit PCM WAV at 16–48 kHz.")
            if not 0 < frames / rate <= 60:
                raise ValueError("Supply a voice note of at most one minute.")
            pcm = recording.readframes(frames)
            if len(pcm) != frames * channels * width:
                raise ValueError("Audio is truncated.")
        audio = folder / "note.wav"
        with wave.open(str(audio), "wb") as clean:
            clean.setparams((channels, width, rate, 0, "NONE", "not compressed"))
            clean.writeframes(pcm)
        def asset(path):
            return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return {"id": folder.name, "consent": True,
                "visual": {**asset(visual), "kind": kind, "pages": pages},
                "audio": asset(audio)}
    except Exception:
        shutil.rmtree(folder)
        raise
