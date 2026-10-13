"""
Unit tests for export modules (TXT, SRT, VTT, JSON, Markdown).
"""

from pathlib import Path
from voicenotes.engine.transcriber import (
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)
from voicenotes.export.exporters import (
    export_to_json,
    export_to_markdown,
    export_to_srt,
    export_to_txt,
    export_to_vtt,
)


def _sample_result() -> TranscriptionResult:
    seg1 = TranscriptionSegment(
        id=1,
        start=0.5,
        end=3.2,
        text="Welcome to the team meeting.",
        speaker="Speaker 1",
        words=[
            TranscriptionWord("Welcome", 0.5, 1.0, 0.95),
            TranscriptionWord("to", 1.0, 1.2, 0.98),
            TranscriptionWord("the", 1.2, 1.4, 0.99),
            TranscriptionWord("team", 1.4, 2.0, 0.96),
            TranscriptionWord("meeting.", 2.0, 3.2, 0.97),
        ],
    )
    seg2 = TranscriptionSegment(
        id=2,
        start=3.5,
        end=6.0,
        text="Thanks, glad to be here.",
        speaker="Speaker 2",
        words=[
            TranscriptionWord("Thanks,", 3.5, 4.0, 0.98),
            TranscriptionWord("glad", 4.0, 4.5, 0.95),
            TranscriptionWord("to", 4.5, 4.8, 0.99),
            TranscriptionWord("be", 4.8, 5.2, 0.97),
            TranscriptionWord("here.", 5.2, 6.0, 0.98),
        ],
    )
    return TranscriptionResult(
        audio_path="samples/meeting.wav",
        duration=6.5,
        language="en",
        language_probability=0.99,
        segments=[seg1, seg2],
        model_name="base",
        num_speakers=2,
        diarization_enabled=True,
    )


def test_export_to_txt():
    res = _sample_result()
    txt = export_to_txt(res, include_timestamps=True, include_speakers=True)
    assert "[00:00 - 00:03] Speaker 1: Welcome to the team meeting." in txt
    assert "[00:03 - 00:06] Speaker 2: Thanks, glad to be here." in txt

    plain = export_to_txt(res, include_timestamps=False, include_speakers=False)
    assert "Speaker 1" not in plain
    assert "Welcome to the team meeting. Thanks, glad to be here." in plain


def test_export_to_srt():
    res = _sample_result()
    srt = export_to_srt(res)
    assert "00:00:00,500 --> 00:00:03,200" in srt
    assert "Speaker 1: Welcome to the team meeting." in srt
    assert "00:00:03,500 --> 00:00:06,000" in srt
    assert "Speaker 2: Thanks, glad to be here." in srt


def test_export_to_vtt():
    res = _sample_result()
    vtt = export_to_vtt(res)
    assert "WEBVTT" in vtt
    assert "00:00:00.500 --> 00:00:03.200" in vtt
    assert "<v Speaker 1>Welcome to the team meeting." in vtt


def test_export_to_json():
    import json

    res = _sample_result()
    json_str = export_to_json(res)
    data = json.loads(json_str)
    assert data["num_speakers"] == 2
    assert len(data["segments"]) == 2
    assert data["segments"][0]["words"][0]["word"] == "Welcome"


def test_export_to_markdown():
    res = _sample_result()
    md = export_to_markdown(res)
    assert "# meeting" in md
    assert "**Speaker 1**" in md
    assert "**Speaker 2**" in md
