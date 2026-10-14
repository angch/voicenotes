"""
Vocabulary and Preferred Spelling Management for VoiceNotes.
Enables users to map misheard, phonetic, or colloquial voice transcriptions
(especially names, terminology, and places) to preferred spellings.

Supports:
- Intelligent word/phrase boundary regex replacement
- Case-sensitive and case-insensitive matching
- Real-time stream substitution
- Comprehensive backfill across completed transcripts and live segments
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from voicenotes.config import config

logger = logging.getLogger(__name__)


def build_phrase_regex(phrase: str, case_sensitive: bool = False) -> re.Pattern:
    r"""
    Build a boundary-aware regular expression for a target word or phrase.
    Handles multi-word phrases and whitespace variations without partial-word collisions.
    Example: 'King Fad' -> r'(?<!\w)King\s+Fad(?!\w)'
    """
    words = phrase.strip().split()
    if not words:
        return re.compile(r"$^")  # Matches nothing

    escaped_words = [re.escape(w) for w in words]
    pattern_str = r"(?<!\w)" + r"\s+".join(escaped_words) + r"(?!\w)"

    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern_str, flags)


def apply_replacement_rules(
    text: str, rules: List[Dict[str, Any]]
) -> Tuple[str, int]:
    """
    Apply an ordered list of replacement rules to input text.
    Returns: (transformed_text, total_replacements_count)
    """
    if not text or not rules:
        return text, 0

    total_count = 0
    result_text = text

    for rule in rules:
        orig = rule.get("original", "").strip()
        repl = rule.get("replacement", "").strip()
        if not orig or orig == repl:
            continue

        case_sens = rule.get("case_sensitive", False)
        pattern = build_phrase_regex(orig, case_sensitive=case_sens)

        # Count occurrences before sub
        matches = len(pattern.findall(result_text))
        if matches > 0:
            result_text = pattern.sub(repl, result_text)
            total_count += matches

    return result_text, total_count


class VocabularyManager:
    """
    Central manager for user-defined preferred spellings and vocabulary rules.
    Loads and persists rules to the application configuration.
    """

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load vocabulary rules from persistent configuration."""
        raw_rules = config.get("vocabulary_replacements", [])
        clean_rules: List[Dict[str, Any]] = []
        seen = set()

        for r in raw_rules:
            if isinstance(r, dict):
                orig = str(r.get("original", "")).strip()
                repl = str(r.get("replacement", "")).strip()
                case_sens = bool(r.get("case_sensitive", False))
                if orig and repl and orig.lower() not in seen:
                    clean_rules.append(
                        {
                            "original": orig,
                            "replacement": repl,
                            "case_sensitive": case_sens,
                        }
                    )
                    seen.add(orig.lower())

        self._rules = clean_rules

    def save(self) -> None:
        """Persist current rules to application configuration."""
        config.set("vocabulary_replacements", self._rules)

    def get_rules(self) -> List[Dict[str, Any]]:
        """Return a copy of all active vocabulary rules."""
        return [dict(r) for r in self._rules]

    def add_or_update_rule(
        self, original: str, replacement: str, case_sensitive: bool = False
    ) -> bool:
        """
        Add a new replacement rule or update an existing one.
        Returns True if rule was added or updated.
        """
        orig = original.strip()
        repl = replacement.strip()
        if not orig or not repl or orig == repl:
            return False

        # Look for existing rule by original (case-insensitive key)
        for rule in self._rules:
            if rule["original"].lower() == orig.lower():
                rule["original"] = orig
                rule["replacement"] = repl
                rule["case_sensitive"] = case_sensitive
                self.save()
                return True

        self._rules.append(
            {
                "original": orig,
                "replacement": repl,
                "case_sensitive": case_sensitive,
            }
        )
        self.save()
        return True

    def remove_rule(self, original: str) -> bool:
        """Remove a rule by its original phrase."""
        orig_lower = original.strip().lower()
        initial_len = len(self._rules)
        self._rules = [r for r in self._rules if r["original"].lower() != orig_lower]
        if len(self._rules) != initial_len:
            self.save()
            return True
        return False

    def clear(self) -> None:
        """Remove all vocabulary rules."""
        self._rules = []
        self.save()

    def apply_to_text(self, text: str) -> Tuple[str, int]:
        """Apply all active rules to arbitrary text."""
        return apply_replacement_rules(text, self._rules)

    def apply_to_segment(self, seg: Any) -> int:
        """
        Apply active rules to a TranscriptionSegment.
        Updates seg.text and seg.words in-place.
        Returns number of replacements made.
        """
        if not seg or not getattr(seg, "text", None):
            return 0

        new_text, count = self.apply_to_text(seg.text)
        seg.text = new_text

        # Also update words list if present
        words = getattr(seg, "words", None)
        if words and count > 0:
            for w in words:
                if hasattr(w, "word") and w.word:
                    w.word, _ = self.apply_to_text(w.word)

        return count

    def apply_to_segments(self, segments: List[Any]) -> int:
        """Apply active rules across a list of TranscriptionSegment objects."""
        total = 0
        for seg in segments:
            total += self.apply_to_segment(seg)
        return total

    def apply_to_result(self, result: Any) -> int:
        """Apply active rules across an entire TranscriptionResult."""
        if not result or not getattr(result, "segments", None):
            return 0
        return self.apply_to_segments(result.segments)

    def export_to_file(self, file_path: Union[str, Path]) -> int:
        """
        Export vocabulary rules to a JSON or CSV file.
        Returns the number of rules exported.
        """
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        rules = self.get_rules()

        if p.suffix.lower() == ".json":
            with open(p, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
        else:
            import csv
            with open(p, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Original", "Preferred", "CaseSensitive"])
                for r in rules:
                    writer.writerow([r["original"], r["replacement"], str(r["case_sensitive"]).lower()])

        return len(rules)

    def import_from_file(
        self, file_path: Union[str, Path], merge: bool = True
    ) -> Tuple[int, int]:
        """
        Import vocabulary rules from a JSON, CSV, TSV, or plain text file.
        Parameters:
        - file_path: path to import from
        - merge: if True, merges/updates existing rules; if False, clears existing rules.
        Returns: (imported_rules_count, total_active_rules_count)
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        new_rules: List[Dict[str, Any]] = []

        if p.suffix.lower() == ".json":
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        orig = str(item.get("original", "")).strip()
                        repl = str(item.get("replacement", "")).strip()
                        case_sens = bool(item.get("case_sensitive", False))
                        if orig and repl and orig != repl:
                            new_rules.append(
                                {"original": orig, "replacement": repl, "case_sensitive": case_sens}
                            )
            elif isinstance(data, dict):
                for k, v in data.items():
                    orig = str(k).strip()
                    repl = str(v).strip()
                    if orig and repl and orig != repl:
                        new_rules.append(
                            {"original": orig, "replacement": repl, "case_sensitive": False}
                        )
        else:
            import csv
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = [line.strip() for line in content.splitlines() if line.strip()]
            for line in lines:
                if "," in line or "\t" in line:
                    delim = "\t" if "\t" in line and "," not in line else ","
                    reader = csv.reader([line], delimiter=delim)
                    try:
                        row = next(reader)
                    except Exception:
                        row = []
                    if len(row) >= 2:
                        orig = row[0].strip()
                        repl = row[1].strip()
                        if orig.lower() in ("original", "voice", "misheard") and repl.lower() in ("preferred", "replacement", "spelling"):
                            continue
                        case_sens = False
                        if len(row) >= 3:
                            case_sens = row[2].strip().lower() in ("true", "1", "yes")
                        if orig and repl and orig != repl:
                            new_rules.append(
                                {"original": orig, "replacement": repl, "case_sensitive": case_sens}
                            )
                            continue

                for sep in ("->", "=>", "=", ":"):
                    if sep in line:
                        parts = line.split(sep, 1)
                        orig = parts[0].strip()
                        repl = parts[1].strip()
                        if orig and repl and orig != repl:
                            new_rules.append(
                                {"original": orig, "replacement": repl, "case_sensitive": False}
                            )
                            break

        if not merge:
            self._rules = []

        imported_count = 0
        for nr in new_rules:
            if self.add_or_update_rule(nr["original"], nr["replacement"], nr["case_sensitive"]):
                imported_count += 1

        return imported_count, len(self._rules)

