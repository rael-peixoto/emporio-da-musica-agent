from datetime import datetime

from emporio.config import STORE_TZ
from emporio.prompt import context_block, static_prompt, system_blocks


def test_static_prompt_contains_rules_and_the_full_manual():
    prompt = static_prompt()
    assert "Regras inegociáveis" in prompt
    assert "## 4. Política de Trocas e Devoluções" in prompt
    assert prompt.rstrip().endswith("</manual>")


def test_only_the_whatsapp_channel_reaches_the_model():
    prompt = static_prompt()
    assert "(67) 3321-4500" in prompt
    assert "3341-4444" not in prompt
    assert "contato@" not in prompt


def test_summary_table_points_to_the_section_3_1_tiers():
    prompt = static_prompt()
    assert "Parcela mínima de R$ 100,00" not in prompt  # the table cell
    assert "parcela mínima de R$ 100,00" in prompt  # §3.1 itself is untouched


def test_every_manual_edit_matches_the_transcription():
    from emporio.config import KNOWLEDGE_DIR
    from emporio.prompt import MANUAL_EDITS

    manual = (KNOWLEDGE_DIR / "politicas.md").read_text(encoding="utf-8")
    assert all(original in manual for original in MANUAL_EDITS)  # a typo here would silently no-op


def test_static_prompt_is_stable_for_caching():
    assert "\r" not in static_prompt()  # identical bytes on Windows and Linux
    assert static_prompt() == static_prompt()


def test_context_when_open():
    friday = datetime(2026, 10, 23, 17, 0, tzinfo=STORE_TZ)
    assert "A loja está aberta agora (hoje até 18:00)." in context_block(friday)




def test_context_when_closed_says_when_humans_return():
    saturday = datetime(2026, 10, 24, 13, 30, tzinfo=STORE_TZ)
    assert "volta segunda-feira, 26/10/2026, às 09:00" in context_block(saturday)


def test_only_the_static_block_is_cached():
    blocks = system_blocks(datetime(2026, 10, 23, 17, 0, tzinfo=STORE_TZ))
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]
