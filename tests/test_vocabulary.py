"""
Tests for Vocabulary Management, Preferred Spelling, and Transcription Backfill.
"""

import pytest
from voicenotes.config import ConfigManager
from voicenotes.engine.transcriber import (
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)
from voicenotes.engine.vocabulary import (
    VocabularyManager,
    apply_replacement_rules,
    build_phrase_regex,
)


def test_build_phrase_regex_word_boundaries():
    pattern = build_phrase_regex("Hicham")
    assert pattern.search("Hello Hicham, how are you?")
    assert pattern.search("hicham is here")
    assert not pattern.search("Hichamovich is here")

    # Boundary protection
    pattern_an = build_phrase_regex("an")
    assert pattern_an.search("this is an apple")
    assert not pattern_an.search("can banana antique")


def test_build_phrase_regex_multi_word():
    pattern = build_phrase_regex("King Fad")
    assert pattern.search("Airport King Fad in Dammam")
    assert pattern.search("Airport King  Fad in Dammam")  # multiple spaces
    assert pattern.search("Airport king fad in Dammam")  # case insensitive
    assert not pattern.search("King Fading away")


def test_apply_replacement_rules():
    rules = [
        {"original": "Hicham", "replacement": "Hisham", "case_sensitive": False},
        {"original": "King Fad", "replacement": "King Fahd", "case_sensitive": False},
        {"original": "Air Asia", "replacement": "AirAsia", "case_sensitive": False},
    ]

    text = "We welcome Hicham to King Fad airport via Air Asia flight."
    transformed, count = apply_replacement_rules(text, rules)

    assert count == 3
    assert transformed == "We welcome Hisham to King Fahd airport via AirAsia flight."


def test_case_sensitive_rule():
    rules = [
        {"original": "KJ", "replacement": "Khairy Jamaluddin", "case_sensitive": True},
    ]

    text_match = "Bersama saya KJ di studio."
    transformed_match, count1 = apply_replacement_rules(text_match, rules)
    assert count1 == 1
    assert transformed_match == "Bersama saya Khairy Jamaluddin di studio."

    text_no_match = "Bersama saya kj di studio."
    transformed_no_match, count2 = apply_replacement_rules(text_no_match, rules)
    assert count2 == 0
    assert transformed_no_match == "Bersama saya kj di studio."


def test_vocabulary_manager_crud(tmp_path):
    cfg_file = tmp_path / "test_settings.json"
    test_config = ConfigManager(config_path=cfg_file)

    # Patch global config temporarily
    import voicenotes.engine.vocabulary as vocab_mod
    original_cfg = vocab_mod.config
    vocab_mod.config = test_config

    try:
        vm = VocabularyManager()
        assert len(vm.get_rules()) == 0

        # Add rule
        added = vm.add_or_update_rule("Hicham", "Hisham")
        assert added is True
        assert len(vm.get_rules()) == 1
        assert vm.get_rules()[0]["replacement"] == "Hisham"

        # Update existing rule
        updated = vm.add_or_update_rule("hicham", "Hisham bin Tariq")
        assert updated is True
        assert len(vm.get_rules()) == 1
        assert vm.get_rules()[0]["replacement"] == "Hisham bin Tariq"

        # Apply to text
        res, count = vm.apply_to_text("Interview with Hicham today.")
        assert count == 1
        assert res == "Interview with Hisham bin Tariq today."

        # Remove rule
        removed = vm.remove_rule("Hicham")
        assert removed is True
        assert len(vm.get_rules()) == 0

    finally:
        vocab_mod.config = original_cfg


def test_vocabulary_manager_apply_to_segments_and_result():
    vm = VocabularyManager()
    vm._rules = [
        {"original": "Hicham", "replacement": "Hisham", "case_sensitive": False},
        {"original": "terbangsa", "replacement": "antarabangsa", "case_sensitive": False},
    ]

    words1 = [
        TranscriptionWord(word="Hello", start=0.0, end=0.5, probability=0.9),
        TranscriptionWord(word="Hicham", start=0.5, end=1.0, probability=0.9),
    ]
    seg1 = TranscriptionSegment(
        id=1,
        start=0.0,
        end=1.0,
        text="Hello Hicham",
        speaker="Speaker 1",
        words=words1,
    )

    seg2 = TranscriptionSegment(
        id=2,
        start=1.2,
        end=2.5,
        text="lapangan terbangsa King Khalid",
        speaker="Speaker 1",
        words=[],
    )

    result = TranscriptionResult(
        audio_path="test.wav",
        duration=2.5,
        language="ms",
        language_probability=0.99,
        segments=[seg1, seg2],
        model_name="small",
    )

    # Backfill result
    total_replaced = vm.apply_to_result(result)
    assert total_replaced == 2

    assert seg1.text == "Hello Hisham"
    assert seg1.words[1].word == "Hisham"
    assert seg2.text == "lapangan antarabangsa King Khalid"


def test_vocabulary_export_json_and_csv(tmp_path):
    vm = VocabularyManager()
    vm._rules = [
        {"original": "Hicham", "replacement": "Hisham", "case_sensitive": False},
        {"original": "KJ", "replacement": "Khairy Jamaluddin", "case_sensitive": True},
    ]

    # Export to JSON
    json_path = tmp_path / "vocab_export.json"
    exported_count = vm.export_to_file(json_path)
    assert exported_count == 2
    assert json_path.exists()

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["original"] == "Hicham"
    assert data[1]["case_sensitive"] is True

    # Export to CSV
    csv_path = tmp_path / "vocab_export.csv"
    exported_csv_count = vm.export_to_file(csv_path)
    assert exported_csv_count == 2
    assert csv_path.exists()

    import csv
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    assert reader[0] == ["Original", "Preferred", "CaseSensitive"]
    assert reader[1] == ["Hicham", "Hisham", "false"]
    assert reader[2] == ["KJ", "Khairy Jamaluddin", "true"]


def test_vocabulary_import_json(tmp_path):
    import json
    vm = VocabularyManager()
    vm._rules = [
        {"original": "OldWord", "replacement": "NewWord", "case_sensitive": False}
    ]

    # Test JSON list format with merge=True
    list_json_path = tmp_path / "rules_list.json"
    list_data = [
        {"original": "Hicham", "replacement": "Hisham", "case_sensitive": False},
        {"original": "KJ", "replacement": "Khairy Jamaluddin", "case_sensitive": True},
    ]
    with open(list_json_path, "w", encoding="utf-8") as f:
        json.dump(list_data, f)

    imported, total = vm.import_from_file(list_json_path, merge=True)
    assert imported == 2
    assert total == 3
    assert any(r["original"] == "OldWord" for r in vm.get_rules())
    assert any(r["original"] == "Hicham" for r in vm.get_rules())

    # Test JSON dict format with merge=False
    dict_json_path = tmp_path / "rules_dict.json"
    dict_data = {
        "Air Asia": "AirAsia",
        "Grab Car": "GrabCar",
    }
    with open(dict_json_path, "w", encoding="utf-8") as f:
        json.dump(dict_data, f)

    imported2, total2 = vm.import_from_file(dict_json_path, merge=False)
    assert imported2 == 2
    assert total2 == 2
    # OldWord should be cleared because merge=False
    assert not any(r["original"] == "OldWord" for r in vm.get_rules())
    assert any(r["original"] == "Air Asia" for r in vm.get_rules())


def test_vocabulary_import_csv_tsv_and_text(tmp_path):
    vm = VocabularyManager()
    vm._rules = []

    # Test CSV with header and case sensitive flag
    csv_path = tmp_path / "vocab.csv"
    csv_path.write_text(
        "Original,Preferred,CaseSensitive\n"
        "Hicham,Hisham,false\n"
        "KJ,Khairy Jamaluddin,true\n",
        encoding="utf-8",
    )
    imported, total = vm.import_from_file(csv_path, merge=False)
    assert imported == 2
    assert total == 2
    kj_rule = next(r for r in vm.get_rules() if r["original"] == "KJ")
    assert kj_rule["case_sensitive"] is True

    # Test TSV format with merge=True
    tsv_path = tmp_path / "vocab.tsv"
    tsv_path.write_text(
        "PMX\tAnwar Ibrahim\ttrue\n"
        "Air Asia\tAirAsia\tfalse\n",
        encoding="utf-8",
    )
    imported_tsv, total_tsv = vm.import_from_file(tsv_path, merge=True)
    assert imported_tsv == 2
    assert total_tsv == 4

    # Test Plain text format with -> and =
    txt_path = tmp_path / "vocab.txt"
    txt_path.write_text(
        "# Custom vocabulary list\n"
        "King Fad -> King Fahd\n"
        "DNB = Digital Nasional Berhad\n"
        "DBKL : Dewan Bandaraya Kuala Lumpur\n",
        encoding="utf-8",
    )
    imported_txt, total_txt = vm.import_from_file(txt_path, merge=True)
    assert imported_txt == 3
    assert total_txt == 7
    assert any(r["replacement"] == "King Fahd" for r in vm.get_rules())
    assert any(r["replacement"] == "Digital Nasional Berhad" for r in vm.get_rules())
    assert any(r["replacement"] == "Dewan Bandaraya Kuala Lumpur" for r in vm.get_rules())

