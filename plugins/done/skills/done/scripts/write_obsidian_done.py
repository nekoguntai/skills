#!/usr/bin/env python3
"""Write a completed-work Markdown note into an Obsidian vault."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path


DEFAULT_NOTE_DIR = "AI maintained documentation/Skills/Sessions"
DEFAULT_INDEX = "AI maintained documentation/Skills/_Index.md"


def existing_default_vault() -> Path | None:
    env_vault = os.environ.get("OBSIDIAN_VAULT")
    candidates = [
        Path(env_vault).expanduser() if env_vault else None,
        Path.home() / "obsidian" / "riannom",
        Path.home() / "riannom2" / "riannom",
        Path.home() / "riannom2",
    ]
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate
    return None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "done"


def read_content(args: argparse.Namespace) -> str:
    if args.content_file:
        return Path(args.content_file).expanduser().read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise SystemExit("No note content provided on stdin. Use --content-file or pipe Markdown.")
    content = sys.stdin.read()
    if not content.strip():
        raise SystemExit("Note content is empty.")
    return content


def resolve_vault(args: argparse.Namespace) -> Path:
    if args.vault:
        vault = Path(args.vault).expanduser()
    else:
        vault = existing_default_vault()
        if vault is None:
            raise SystemExit("No Obsidian vault found. Set OBSIDIAN_VAULT or pass --vault.")
    if not vault.is_dir():
        raise SystemExit(f"Vault does not exist or is not a directory: {vault}")
    return vault


def write_unique_note(directory: Path, base_name: str, content: str, overwrite: bool) -> Path:
    if overwrite:
        note_path = directory / f"{base_name}.md"
        note_path.write_text(content, encoding="utf-8")
        return note_path

    for index in range(1, 1000):
        suffix = "" if index == 1 else f"-{index}"
        note_path = directory / f"{base_name}{suffix}.md"
        try:
            with note_path.open("x", encoding="utf-8") as handle:
                handle.write(content)
            return note_path
        except FileExistsError:
            continue
    raise SystemExit(f"Could not find an available note name for {directory / base_name}.md")


def normalize_note(content: str, title: str) -> str:
    stripped = content.strip()
    if stripped.startswith("# "):
        return stripped + "\n"
    return f"# {title}\n\n{stripped}\n"


def wiki_target(vault: Path, note_path: Path) -> str:
    relative = note_path.relative_to(vault).with_suffix("")
    return relative.as_posix()


def append_index(vault: Path, index_relative: str, note_path: Path, title: str) -> None:
    index_path = vault / index_relative
    index_path.parent.mkdir(parents=True, exist_ok=True)
    link = f"- [[{wiki_target(vault, note_path)}|{title}]]"
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Index\n"
    if link in existing:
        return
    separator = "" if existing.endswith("\n") else "\n"
    index_path.write_text(f"{existing}{separator}{link}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="Human-readable note title.")
    parser.add_argument("--project", help="Project or area name to include in the filename.")
    parser.add_argument("--vault", help="Obsidian vault path. Defaults to OBSIDIAN_VAULT or known local vaults.")
    parser.add_argument("--note-dir", default=os.environ.get("DONE_OBSIDIAN_DIR", DEFAULT_NOTE_DIR))
    parser.add_argument("--date", default=date.today().isoformat(), help="Date prefix in YYYY-MM-DD format.")
    parser.add_argument("--content-file", help="Read Markdown content from this file instead of stdin.")
    parser.add_argument("--index", help=f"Optional index file inside the vault, e.g. {DEFAULT_INDEX!r}.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the computed note path if it exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = resolve_vault(args)
    note_dir = vault / args.note_dir
    note_dir.mkdir(parents=True, exist_ok=True)

    name_parts = [args.date]
    if args.project:
        name_parts.append(slugify(args.project))
    name_parts.append(slugify(args.title))
    content = normalize_note(read_content(args), args.title)
    note_path = write_unique_note(note_dir, "-".join(name_parts), content, args.overwrite)
    if args.index:
        append_index(vault, args.index, note_path, args.title)

    print(note_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
