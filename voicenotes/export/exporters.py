"""
Export formatters for transcription results (TXT, SRT, VTT, JSON, Markdown).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from voicenotes.engine.transcriber import TranscriptionResult


def _seconds_to_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """Format seconds into WebVTT timestamp: HH:MM:SS.mmm"""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def export_to_txt(
    result: TranscriptionResult,
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> str:
    """Export to plain text."""
    if not include_timestamps and not include_speakers:
        return result.plain_text

    lines = []
    for seg in result.segments:
        text_clean = seg.text.strip()
        parts = []
        if include_timestamps:
            parts.append(seg.timestamp_str)
        if include_speakers and seg.speaker:
            parts.append(f"{seg.speaker}:")
        parts.append(text_clean)
        lines.append(" ".join(parts))
    return "\n".join(lines)


def export_to_srt(result: TranscriptionResult, include_speakers: bool = True) -> str:
    """Export to SubRip Subtitle (.srt) format."""
    blocks = []
    for idx, seg in enumerate(result.segments, start=1):
        start_str = _seconds_to_srt_time(seg.start)
        end_str = _seconds_to_srt_time(seg.end)
        text = seg.text.strip()
        if include_speakers and seg.speaker:
            text = f"{seg.speaker}: {text}"
        block = f"{idx}\n{start_str} --> {end_str}\n{text}\n"
        blocks.append(block)
    return "\n".join(blocks)


def export_to_vtt(result: TranscriptionResult, include_speakers: bool = True) -> str:
    """Export to WebVTT (.vtt) format."""
    lines = ["WEBVTT\n"]
    for seg in result.segments:
        start_str = _seconds_to_vtt_time(seg.start)
        end_str = _seconds_to_vtt_time(seg.end)
        text = seg.text.strip()
        if include_speakers and seg.speaker:
            text = f"<v {seg.speaker}>{text}"
        lines.append(f"{start_str} --> {end_str}\n{text}\n")
    return "\n".join(lines)


def export_to_json(result: TranscriptionResult) -> str:
    """Export to structured JSON with word-level timestamps."""
    data = {
        "audio_path": result.audio_path,
        "duration": result.duration,
        "language": result.language,
        "language_probability": result.language_probability,
        "model_name": result.model_name,
        "num_speakers": result.num_speakers,
        "diarization_enabled": result.diarization_enabled,
        "segments": [
            {
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "speaker": s.speaker,
                "text": s.text.strip(),
                "words": [
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    }
                    for w in s.words
                ],
            }
            for s in result.segments
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_to_markdown(result: TranscriptionResult) -> str:
    """Export to formatted Markdown document."""
    title = Path(result.audio_path).stem if result.audio_path else "Voice Notes Transcript"
    duration_min = f"{result.duration / 60:.1f} min" if result.duration else "N/A"

    lines = [
        f"# {title}",
        "",
        "| Metric | Details |",
        "| :--- | :--- |",
        f"| **Audio Duration** | {duration_min} ({result.duration:.1f}s) |",
        f"| **Detected Language** | {result.language.upper()} ({result.language_probability*100:.0f}%) |",
        f"| **Whisper Model** | {result.model_name.capitalize()} |",
        f"| **Speakers Detected** | {result.num_speakers} |",
        "",
        "---",
        "",
        "## Transcript",
        "",
    ]

    for seg in result.segments:
        speaker_badge = f"**{seg.speaker}** " if seg.speaker else ""
        lines.append(f"`{seg.timestamp_str}` {speaker_badge}: {seg.text.strip()}")
        lines.append("")

    return "\n".join(lines)


def save_export_to_file(
    result: TranscriptionResult,
    target_path: Union[str, Path],
    format_type: Optional[str] = None,
) -> None:
    """Save transcript to file based on extension or explicit format type."""
    p = Path(target_path)
    ext = (format_type or p.suffix.lstrip(".").lower()).lower()

    if ext == "srt":
        content = export_to_srt(result)
    elif ext == "vtt":
        content = export_to_vtt(result)
    elif ext == "json":
        content = export_to_json(result)
    elif ext in ("md", "markdown"):
        content = export_to_markdown(result)
    else:  # txt or default
        content = export_to_txt(result)

    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
