"""
Pytest configuration and session fixtures for VoiceNotes test suite.
"""

from __future__ import annotations

import os
import sys


def pytest_configure(config):
    """
    Configure test execution environment.
    Automatically set QT_QPA_PLATFORM to 'offscreen' when running in CI
    or headless environments to avoid Qt display connection aborts.
    """
    if "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("CI") or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")):
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
