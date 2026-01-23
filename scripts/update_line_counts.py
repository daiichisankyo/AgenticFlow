#!/usr/bin/env python3
"""Update line counts in documentation files.

This script:
1. Counts lines in docs/examples/*.py files
2. Updates corresponding line count references in docs/en/*.md files

Usage:
    uv run python scripts/update_line_counts.py
    uv run python scripts/update_line_counts.py --check  # Verify without modifying
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "examples"
DOCS_DIR = PROJECT_ROOT / "docs" / "en"

LINE_COUNT_FILES = {
    "pure_sdk_chatkit.py": "Pure SDK",
    "agenticflow_flow.py": "Flow",
    "agenticflow_chatkit.py": "ChatKit Server",
    "agenticflow_cli.py": "CLI",
}


def count_lines(filepath: Path) -> int:
    """Count non-empty lines in a file."""
    content = filepath.read_text().strip()
    return len(content.splitlines())


def get_line_counts() -> dict[str, int]:
    """Get line counts for all example files."""
    counts = {}
    for filename in LINE_COUNT_FILES:
        filepath = EXAMPLES_DIR / filename
        if filepath.exists():
            counts[filename] = count_lines(filepath)
    return counts


def update_markdown_file(filepath: Path, counts: dict[str, int], check_only: bool) -> bool:
    """Update line count references in a markdown file.

    Returns True if file was modified (or would be modified in check mode).
    """
    content = filepath.read_text()
    original = content

    pure_sdk_count = counts.get("pure_sdk_chatkit.py", 120)
    flow_count = counts.get("agenticflow_flow.py", 40)
    chatkit_count = counts.get("agenticflow_chatkit.py", 15)
    cli_count = counts.get("agenticflow_cli.py", 10)

    replacements = [
        (r"~\d+ lines of ceremony", f"~{pure_sdk_count} lines of ceremony"),
        (r"~\d+ lines :material-check:", f"~{flow_count} lines :material-check:"),
        (r"Pure SDK — ~\d+ lines", f"Pure SDK — ~{pure_sdk_count} lines"),
        (r"Flow — \d+ lines", f"Flow — {flow_count} lines"),
        (r"Flow Definition — \d+ lines", f"Flow Definition — {flow_count} lines"),
        (r"ChatKit Server — \d+ lines", f"ChatKit Server — {chatkit_count} lines"),
        (r"CLI — \d+ lines", f"CLI — {cli_count} lines"),
        (r"CLI Usage — \d+ lines", f"CLI Usage — {cli_count} lines"),
        (r"\| Lines of code \| ~\d+ \| ~\d+ \|", f"| Lines of code | ~{pure_sdk_count} | ~{flow_count} |"),
        (r"\| \*\*Lines of code\*\* \| ~\d+ \| ~\d+ \|", f"| **Lines of code** | ~{pure_sdk_count} | ~{flow_count} |"),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    if content != original:
        if check_only:
            print(f"Would update: {filepath.relative_to(PROJECT_ROOT)}")
            return True
        filepath.write_text(content)
        print(f"Updated: {filepath.relative_to(PROJECT_ROOT)}")
        return True

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Update line counts in documentation")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if updates are needed without modifying files",
    )
    args = parser.parse_args()

    counts = get_line_counts()

    print("Line counts:")
    for filename, count in counts.items():
        label = LINE_COUNT_FILES[filename]
        print(f"  {label}: {count} lines ({filename})")
    print()

    modified = False
    for md_file in DOCS_DIR.rglob("*.md"):
        if update_markdown_file(md_file, counts, args.check):
            modified = True

    if args.check and modified:
        print("\nLine counts need updating. Run without --check to apply.")
        return 1

    if not modified:
        print("All line counts are up to date.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
