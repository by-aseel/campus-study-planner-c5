"""Save a provider key locally using a hidden prompt; no external requests."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile
import warnings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def main() -> int:
    parser = argparse.ArgumentParser(description="Securely create this project's local .env file.")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing .env file.")
    parser.add_argument("--provider", choices=("groq", "openrouter"), default="groq")
    args = parser.parse_args()
    if ENV_PATH.exists() and not args.force:
        print("A .env file already exists and was preserved. Use --force only if you intend to replace it.", file=sys.stderr)
        return 1
    try:
        # Refuse getpass's echoing fallback if the terminal cannot hide input.
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass(f"Paste your {args.provider} API key (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("No key was saved. Run this script in an interactive terminal that supports hidden input.", file=sys.stderr)
        return 1
    if not key or any(character.isspace() or not character.isprintable() for character in key):
        print("No key was saved. The API key must be nonempty and contain no whitespace or control characters.", file=sys.stderr)
        return 1
    model = "openai/gpt-oss-20b" if args.provider == "groq" else "deepseek/deepseek-v4.1-flash"
    prefix = "GROQ" if args.provider == "groq" else "OPENROUTER"
    contents = (
        "# Local credentials. This file must never be committed or shared.\n"
        f"LLM_PROVIDER={args.provider}\n"
        f"{prefix}_API_KEY={json.dumps(key)}\n"
        f"{prefix}_MODEL={model}\n"
    )
    temporary_path: Path | None = None
    try:
        if args.force:
            descriptor, filename = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=PROJECT_ROOT)
            temporary_path = Path(filename)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(contents)
            os.replace(temporary_path, ENV_PATH)
            temporary_path = None
        else:
            # Exclusive creation also prevents an overwrite if another process
            # creates .env after the initial existence check.
            descriptor = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(contents)
    except FileExistsError:
        print("A .env file already exists and was preserved. No key was saved.", file=sys.stderr)
        return 1
    except OSError:
        print("Could not save .env. Check that the project folder is writable.", file=sys.stderr)
        return 1
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print(f"Saved the key locally in .env. Selected model: {model}. The key was not displayed or sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
