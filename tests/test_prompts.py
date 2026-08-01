"""Tests de app.ai.prompts (tâche 3.7)."""
from app.ai.prompts import SYSTEM_PROMPT_SAV, build_system_prompt, build_title_prompt


def test_build_system_prompt_defaults_to_french():
    prompt = build_system_prompt()

    assert prompt.startswith(SYSTEM_PROMPT_SAV)
    assert "Réponds en français" in prompt


def test_build_system_prompt_adapts_to_known_language():
    prompt = build_system_prompt("en")

    assert "Réponds en anglais" in prompt


def test_build_system_prompt_falls_back_to_french_for_unknown_language():
    prompt = build_system_prompt("de")

    assert "Réponds en français" in prompt


def test_system_prompt_mentions_escalation_to_ticket_or_technician():
    assert "ticket" in SYSTEM_PROMPT_SAV.lower()
    assert "technicien" in SYSTEM_PROMPT_SAV.lower()


def test_build_title_prompt_defaults_to_french():
    prompt = build_title_prompt()

    assert "français" in prompt


def test_build_title_prompt_adapts_to_known_language():
    prompt = build_title_prompt("en")

    assert "anglais" in prompt


def test_build_title_prompt_forbids_generic_titles():
    prompt = build_title_prompt()

    assert "salutation générique" in prompt or "générique" in prompt


__all__: list[str] = []
