"""Utility helpers for loading Whisper models and running transcriptions."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from faster_whisper import WhisperModel


class TranscriptionError(Exception):
    """Raised when audio transcription fails for a known reason."""


ModelConfig = Tuple[str, str]


def load_model(model_size: str = "base", compute_type: str = "int8") -> WhisperModel:
    """Load a Whisper model with the provided configuration."""
    if not model_size:
        raise ValueError("model_size must be provided")

    return WhisperModel(model_size, device="auto", compute_type=compute_type)


def _merge_segments(segments: Iterable) -> str:
    """Join Whisper segments into a single string."""
    parts = []
    for segment in segments:
        text = getattr(segment, "text", "")
        text = text.strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def transcribe_audio(
    model: WhisperModel,
    audio_path: Path,
    *,
    beam_size: int = 5,
    best_of: int = 5,
) -> Tuple[str, float]:
    """
    Transcribe an audio file, returning the text and duration in seconds.

    Args:
        model: Loaded Whisper model.
        audio_path: Path to the audio file.
        beam_size: Beam size for decoding.
        best_of: Number of candidates to retain.

    Returns:
        tuple[str, float]: Transcribed text and duration seconds.
    """
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    try:
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=beam_size,
            best_of=best_of,
        )
    except Exception as exc:  # pragma: no cover - surfacing to UI
        raise TranscriptionError("Failed to transcribe audio") from exc

    return _merge_segments(segments), info.duration
