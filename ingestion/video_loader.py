"""
ingestion/video_loader.py

Transcribes a lecture video/audio file locally using faster-whisper
(no API, no upload, runs on CPU). Returns segments in the same
(number, text) shape the PDF/PPTX loaders use, so it plugs into the
same chunker without changes.

Notes:
    - Works directly on video files (mp4, etc.) as well as audio
      (mp3, wav) — faster-whisper decodes the audio track itself.
    - First run will download the chosen Whisper model (a few hundred
      MB to ~1.5GB depending on size), then it's cached locally.
    - Model size trade-off:
        "tiny"/"base"  -> fast, lower accuracy, fine for a demo
        "small"/"medium" -> slower, noticeably better accuracy
"""

import os
from typing import List, Tuple

from faster_whisper import WhisperModel

DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

_model_cache = {}


def _get_model(model_size: str) -> WhisperModel:
    """Loads (and caches) a Whisper model so repeated calls don't reload it."""
    if model_size not in _model_cache:
        # CPU + int8 keeps this usable on a normal laptop without a GPU
        _model_cache[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _model_cache[model_size]


def transcribe_video(
    file_path: str,
    model_size: str = DEFAULT_MODEL_SIZE,
) -> List[Tuple[int, str]]:
    """
    Transcribes a video/audio file into segments.

    Returns:
        A list of (segment_number, segment_text) tuples, 1-indexed,
        in the same shape as pdf_loader/pptx_loader output.
    """
    model = _get_model(model_size)
    segments, info = model.transcribe(file_path, beam_size=5)

    print(f"  Detected language: {info.language} (confidence={info.language_probability:.2f})")

    output = []
    for i, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if text:
            output.append((i, text))

    return output


def save_transcript(
    segments: List[Tuple[int, str]],
    output_path: str,
) -> None:
    """Saves the plain transcript to a text file for reference/debugging."""
    with open(output_path, "w", encoding="utf-8") as f:
        for seg_num, text in segments:
            f.write(f"[{seg_num}] {text}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_loader.py <path_to_video_or_audio>")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"Transcribing {file_path} (this can take a while on CPU)...")
    result = transcribe_video(file_path)
    print(f"Produced {len(result)} segments.")
    if result:
        preview = result[0][1][:150]
        print(f"First segment: {preview}...")
