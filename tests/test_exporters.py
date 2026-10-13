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


def test_compress_audio_file(tmp_path):
    """Test audio compression to .ogg and .mp3 formats."""
    import os
    from voicenotes.engine.audio_utils import compress_audio_file, load_audio

    jfk_sample = Path("samples/jfk.flac")
    assert jfk_sample.exists()
    orig_size = os.path.getsize(jfk_sample)

    # 1. Compress to OGG
    ogg_target = tmp_path / "compressed.ogg"
    out_ogg = compress_audio_file(jfk_sample, output_path=ogg_target, target_format="ogg")
    assert out_ogg.exists()
    ogg_size = os.path.getsize(out_ogg)
    assert ogg_size < orig_size * 0.25  # At least 75% smaller
    audio_ogg, sr_ogg = load_audio(out_ogg)
    assert sr_ogg == 16000
    assert len(audio_ogg) > 0

    # 2. Compress to MP3
    mp3_target = tmp_path / "compressed.mp3"
    out_mp3 = compress_audio_file(jfk_sample, output_path=mp3_target, target_format="mp3")
    assert out_mp3.exists()
    mp3_size = os.path.getsize(out_mp3)
    assert mp3_size < orig_size * 0.25
    audio_mp3, sr_mp3 = load_audio(out_mp3)
    assert sr_mp3 == 16000
    assert len(audio_mp3) > 0


def test_create_archive_bundle(tmp_path):
    """Test archival package generation containing compressed audio, transcripts, and metadata."""
    import json
    import os
    import zipfile
    from voicenotes.export.exporters import create_archive_bundle

    res = _sample_result()
    jfk_sample = Path("samples/jfk.flac")

    # 1. Archive with OGG compression (default)
    zip_path_ogg = tmp_path / "meeting_archive_ogg.zip"
    created_ogg = create_archive_bundle(
        result=res,
        audio_path=jfk_sample,
        target_zip_path=zip_path_ogg,
        audio_format="ogg",
        notes="Important sync meeting notes",
    )
    assert created_ogg.exists()

    with zipfile.ZipFile(created_ogg, "r") as zf:
        namelist = zf.namelist()
        assert "audio.ogg" in namelist
        assert "transcript.txt" in namelist
        assert "transcript_plain.txt" in namelist
        assert "transcript.md" in namelist
        assert "transcript.srt" in namelist
        assert "transcript.vtt" in namelist
        assert "transcript.json" in namelist
        assert "archive_metadata.json" in namelist
        assert "notes.txt" in namelist

        meta = json.loads(zf.read("archive_metadata.json").decode("utf-8"))
        assert meta["audio"]["compressed_format"] == "ogg"
        assert meta["audio"]["compressed_size_bytes"] < os.path.getsize(jfk_sample)

    # 2. Archive with MP3 compression
    zip_path_mp3 = tmp_path / "meeting_archive_mp3.zip"
    created_mp3 = create_archive_bundle(
        result=res,
        audio_path=jfk_sample,
        target_zip_path=zip_path_mp3,
        audio_format="mp3",
    )
    assert created_mp3.exists()

    with zipfile.ZipFile(created_mp3, "r") as zf:
        assert "audio.mp3" in zf.namelist()
        meta = json.loads(zf.read("archive_metadata.json").decode("utf-8"))
        assert meta["audio"]["compressed_format"] == "mp3"

