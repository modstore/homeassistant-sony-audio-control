"""Pytest configuration for lightweight unit tests.

The tests exercise the reusable Sony helper modules without importing the full
Home Assistant integration package, which would require a running HA test env.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "sony_audio_control"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components", custom_components)

sony_audio_control = types.ModuleType("custom_components.sony_audio_control")
sony_audio_control.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components.sony_audio_control", sony_audio_control)
