"""emporio.setup writes .env without touching anything else. Uses temporary files only."""

from emporio.setup import set_env_values


def test_missing_env_starts_from_the_template(tmp_path):
    template = tmp_path / ".env.example"
    template.write_text("# comment\nEMPORIO_ACCESS_CODE=\nANTHROPIC_API_KEY=\n", encoding="utf-8")
    env = tmp_path / ".env"
    set_env_values(env, {"EMPORIO_ACCESS_CODE": "abc123"}, template=template)
    assert env.read_text(encoding="utf-8") == "# comment\nEMPORIO_ACCESS_CODE=abc123\nANTHROPIC_API_KEY=\n"


def test_existing_values_and_comments_are_kept(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# EMPORIO_ACCESS_CODE=old-in-comment\nMODEL=claude-haiku-5-5\n"
                   "EMPORIO_ACCESS_CODE=old\n", encoding="utf-8")
    set_env_values(env, {"EMPORIO_ACCESS_CODE": "new"}, template=tmp_path / "none")
    assert env.read_text(encoding="utf-8") == (
        "# EMPORIO_ACCESS_CODE=old-in-comment\nMODEL=claude-haiku-5-5\nEMPORIO_ACCESS_CODE=new\n")


def test_missing_key_is_appended(tmp_path):
    env = tmp_path / ".env"
    env.write_text("MODEL=claude-haiku-5-5\n", encoding="utf-8")
    set_env_values(env, {"ANTHROPIC_API_KEY": "k"}, template=tmp_path / "none")
    assert env.read_text(encoding="utf-8") == "MODEL=claude-haiku-5-5\nANTHROPIC_API_KEY=k\n"
