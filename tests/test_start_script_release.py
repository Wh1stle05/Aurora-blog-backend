from pathlib import Path


def test_start_script_uses_non_interactive_certbot_flags():
    script = Path("scripts/start.sh").read_text()

    assert "--non-interactive" in script
    assert "--keep-until-expiring" in script
