"""Write the access code (or your own API key) to .env, so nobody has to edit files by hand.

Usage:
    python -m emporio.setup                      # asks for the access code (typing is hidden)
    python -m emporio.setup --access-code CODE   # non-interactive
    python -m emporio.setup --api-key            # asks for your own Anthropic key (direct mode)

Values are never printed.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from emporio.config import PROJECT_ROOT

ENV_FILE = PROJECT_ROOT / ".env"
EXAMPLE_FILE = PROJECT_ROOT / ".env.example"


def set_env_values(path: Path, values: dict[str, str], template: Path = EXAMPLE_FILE) -> None:
    """Set KEY=value lines in a .env file, keeping every other line as it is.

    A missing .env starts from the template (.env.example).
    """
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    elif template.exists():
        lines = template.read_text(encoding="utf-8").splitlines()
    else:
        lines = []
    pending = dict(values)
    updated = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in pending and not line.lstrip().startswith("#"):
            updated.append(f"{key}={pending.pop(key)}")
        else:
            updated.append(line)
    updated += [f"{key}={value}" for key, value in pending.items()]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m emporio.setup",
                                     description="Save the access code or your own API key to .env.")
    parser.add_argument("--access-code", help="the code sent with the submission")
    parser.add_argument("--api-key", action="store_true",
                        help="use your own Anthropic API key instead (asked with hidden input)")
    args = parser.parse_args(argv)

    if args.api_key:
        key = getpass.getpass("Cole sua chave da API da Anthropic (não aparece na tela): ").strip()
        if not key:
            print("Nenhuma chave informada; nada foi alterado.", file=sys.stderr)
            return 1
        set_env_values(ENV_FILE, {"ANTHROPIC_API_KEY": key})
        print("Pronto! Sua chave foi salva em .env (modo direto).")
    else:
        code = (args.access_code or
                getpass.getpass("Cole o código de acesso (não aparece na tela): ")).strip()
        if not code:
            print("Nenhum código informado; nada foi alterado.", file=sys.stderr)
            return 1
        set_env_values(ENV_FILE, {"EMPORIO_ACCESS_CODE": code})
        print("Pronto! O código de acesso foi salvo em .env (modo proxy).")
    print("Agora rode:  .venv\\Scripts\\python -m emporio.web   (chat no navegador)")
    print("        ou:  .venv\\Scripts\\python -m emporio       (chat no terminal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
