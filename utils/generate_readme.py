"""
Utility script to sync the app-intro section across README.md and docs/index.md,
using the shared intro text defined in utils.help_menus.get_app_intro_markdown()
and the values from resource/app_schema_{webapp_version}.json.

IMPORTANT: the source of truth of the app and its documentation is utils/help_menus.py.
Change any content there and re-run utils/generate_readme.py to push changes into README.md and docs/index.md.

Usage (run from the repo root):
    python3 utils/generate_readme.py -v v0.9.2

This script updates:

  README.md
  ---------
  1) The header version in the resource/app_schema_<webapp_version>.json"
     to match --webapp-version.
  2) The intro block between markers:
       <!-- APP_INTRO_START -->
       <!-- APP_INTRO_END -->

  docs/index.md
  -------------
  3) The intro block between markers:
       <!-- DOCS_INTRO_START -->
       <!-- DOCS_INTRO_END -->
     using utils.help_menus.get_docs_intro_markdown() — trimmed variant
     of "five steps"/"two types of issues" intro.
  4) The steps-table block between markers:
       <!-- DOCS_STEPS_TABLE_START -->
       <!-- DOCS_STEPS_TABLE_END -->
     using utils.help_menus.get_steps_table_markdown() — the same table
     shown in the App intro, so both stay in sync.
  5) The two-types-of-issues block between markers:
       <!-- DOCS_TWO_TYPES_START -->
       <!-- DOCS_TWO_TYPES_END -->
     using utils.help_menus.get_two_types_of_issues_markdown() — the same
     wording and bullet-list format shown in the App intro, so both stay
     in sync.

Before sync'ing <version>, this script checks that the CHANGELOG.md's
latest entry matches --webapp-version.

If any marker or header cannot be located, the script raises RuntimeError
and leaves both files unchanged.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Tuple


def build_cde_url(schema: dict) -> str:
    """Build the public Google Sheets URL for the CDE definition."""
    spreadsheet_id = schema["cde_definition"]["spreadsheet_id"]
    return (
        "https://docs.google.com/spreadsheets/d/"
        f"{spreadsheet_id}/edit?usp=sharing"
    )


def load_schema(schema_path: str) -> dict:
    """Load the app_schema JSON from the given path."""
    with open(schema_path, "r", encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    return schema


def find_marked_block(text: str, start_marker: str, end_marker: str) -> Tuple[int, int]:
    """Locate the region between start_marker and end_marker in text.

    Returns (region_start, region_end) where the region is the content
    between (not including) the markers. Returns (-1, -1) if not found.
    """
    start_index = text.find(start_marker)
    end_index = text.find(end_marker)

    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return -1, -1

    region_start = start_index + len(start_marker)
    region_end = end_index
    return region_start, region_end


def replace_block(text: str, region_start: int, region_end: int, new_content: str) -> str:
    """Replace the region [region_start:region_end] in text with new_content."""
    return (
        text[:region_start]
        + "\n\n"
        + new_content.rstrip()
        + "\n\n"
        + text[region_end:]
    )


def replace_readme_header_version(readme_text: str, webapp_version: str) -> str:
    """
    Replace the version in the README header line:
        'Metadata validator for ASAP CRN metadata (vX.Y) or (vX.Y.Z)'
    using the provided webapp_version.
    """
    pattern = r"(Metadata validator for ASAP CRN metadata \(v[0-9]+\.[0-9]+(\.[0-9]+)?\))"
    replacement = f"Metadata validator for ASAP CRN metadata ({webapp_version})"
    updated_text, num_subs = re.subn(pattern, replacement, readme_text, count=1)

    if num_subs == 0:
        raise RuntimeError(
            "Could not replace README header version. "
            "Expected header like: 'Metadata validator for ASAP CRN metadata (v0.9.2)'."
        )

    return updated_text


def get_latest_changelog_version(repo_root: str) -> str:
    """
    Return the version from CHANGELOG.md's first (most recent) entry.

    CHANGELOG.md lists entries newest-first, each headed by a line like
    '## v0.9.3 — May 4th, 2026 · CDE v4.4'. This returns the version from
    the first such heading found.

    Parameters
    ----------
    repo_root : str
        Absolute path to the repository root.

    Returns
    -------
    str
        Version string from the first "## v..." heading (e.g. "v0.9.3").
    """
    changelog_path = os.path.join(repo_root, "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        raise RuntimeError(f"CHANGELOG.md not found at: {changelog_path}")

    with open(changelog_path, "r", encoding="utf-8") as f:
        changelog_text = f.read()

    version_match = re.search(
        r"^##\s+(v[0-9]+(?:\.[0-9]+){0,2})\b",
        changelog_text,
        re.MULTILINE,
    )
    if version_match is None:
        raise RuntimeError(
            "Could not find a version heading in CHANGELOG.md. Expected a "
            "line like: '## v0.9.3 — May 4th, 2026 · CDE v4.4'."
        )

    return version_match.group(1)


def validate_changelog_version(repo_root: str, webapp_version: str) -> None:
    """
    Raise RuntimeError if CHANGELOG.md's latest entry doesn't match webapp_version.

    This is a check, not a sync: CHANGELOG.md is never rewritten here (its
    entries are hand-written release notes, not derived content like the
    intro/steps-table/two-types-of-issues blocks). Catches releasing a new
    webapp_version without having first added its changelog entry.

    Parameters
    ----------
    repo_root : str
        Absolute path to the repository root.
    webapp_version : str
        Version passed via --webapp-version.

    Returns
    -------
    None
    """
    latest_changelog_version = get_latest_changelog_version(repo_root=repo_root)

    if latest_changelog_version != webapp_version:
        raise RuntimeError(
            f"CHANGELOG.md's latest entry is '{latest_changelog_version}', but "
            f"--webapp-version is '{webapp_version}'. Add a "
            f"'## {webapp_version} — <date> · CDE <cde_version>' entry to "
            "CHANGELOG.md (repo root) describing this release, then re-run."
        )

    print(f"CHANGELOG.md is up to date (latest entry: {latest_changelog_version}).")


def update_readme(repo_root: str, intro_markdown: str, webapp_version: str) -> None:
    """Update README.md: replace header version and APP_INTRO block."""
    readme_path = os.path.join(repo_root, "README.md")
    if not os.path.exists(readme_path):
        raise RuntimeError(f"README not found at: {readme_path}")

    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    text = replace_readme_header_version(
        readme_text=text,
        webapp_version=webapp_version,
    )

    region_start, region_end = find_marked_block(
        text=text,
        start_marker="<!-- APP_INTRO_START -->",
        end_marker="<!-- APP_INTRO_END -->",
    )
    if region_start == -1:
        raise RuntimeError(
            "Could not locate <!-- APP_INTRO_START --> ... <!-- APP_INTRO_END --> "
            "markers in README.md."
        )

    text = replace_block(text, region_start, region_end, intro_markdown)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("README.md updated.")


def update_docs_index(repo_root: str, intro_markdown: str) -> None:
    """Update docs/index.md: replace DOCS_INTRO block."""
    index_path = os.path.join(repo_root, "docs", "index.md")
    if not os.path.exists(index_path):
        raise RuntimeError(f"docs/index.md not found at: {index_path}")

    with open(index_path, "r", encoding="utf-8") as f:
        text = f.read()

    region_start, region_end = find_marked_block(
        text=text,
        start_marker="<!-- DOCS_INTRO_START -->",
        end_marker="<!-- DOCS_INTRO_END -->",
    )
    if region_start == -1:
        raise RuntimeError(
            "Could not locate <!-- DOCS_INTRO_START --> ... <!-- DOCS_INTRO_END --> "
            "markers in docs/index.md."
        )

    text = replace_block(text, region_start, region_end, intro_markdown)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("docs/index.md updated.")


def update_docs_steps_table(repo_root: str, steps_table_markdown: str) -> None:
    """Update docs/index.md: replace DOCS_STEPS_TABLE block."""
    index_path = os.path.join(repo_root, "docs", "index.md")
    if not os.path.exists(index_path):
        raise RuntimeError(f"docs/index.md not found at: {index_path}")

    with open(index_path, "r", encoding="utf-8") as f:
        text = f.read()

    region_start, region_end = find_marked_block(
        text=text,
        start_marker="<!-- DOCS_STEPS_TABLE_START -->",
        end_marker="<!-- DOCS_STEPS_TABLE_END -->",
    )
    if region_start == -1:
        raise RuntimeError(
            "Could not locate <!-- DOCS_STEPS_TABLE_START --> ... <!-- DOCS_STEPS_TABLE_END --> "
            "markers in docs/index.md."
        )

    text = replace_block(text, region_start, region_end, steps_table_markdown)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("docs/index.md steps table updated.")


def update_docs_two_types_of_issues(repo_root: str, two_types_of_issues_markdown: str) -> None:
    """Update docs/index.md: replace DOCS_TWO_TYPES block."""
    index_path = os.path.join(repo_root, "docs", "index.md")
    if not os.path.exists(index_path):
        raise RuntimeError(f"docs/index.md not found at: {index_path}")

    with open(index_path, "r", encoding="utf-8") as f:
        text = f.read()

    region_start, region_end = find_marked_block(
        text=text,
        start_marker="<!-- DOCS_TWO_TYPES_START -->",
        end_marker="<!-- DOCS_TWO_TYPES_END -->",
    )
    if region_start == -1:
        raise RuntimeError(
            "Could not locate <!-- DOCS_TWO_TYPES_START --> ... <!-- DOCS_TWO_TYPES_END --> "
            "markers in docs/index.md."
        )

    text = replace_block(text, region_start, region_end, two_types_of_issues_markdown)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("docs/index.md two-types-of-issues block updated.")


def sync_all(repo_root: str, webapp_version: str) -> None:
    """Load schema, build intro markdown, and sync README.md + docs/index.md."""
    # Guard, not a sync — fail fast before touching any file if CHANGELOG.md
    # hasn't been updated for this release yet.
    validate_changelog_version(repo_root=repo_root, webapp_version=webapp_version)

    schema_filename = f"app_schema_{webapp_version}.json"
    schema_path = os.path.join(repo_root, "resource", schema_filename)

    if not os.path.exists(schema_path):
        raise RuntimeError(f"Schema file not found at: {schema_path}")

    schema = load_schema(schema_path=schema_path)
    cde_version = schema["cde_definition"]["cde_version"]
    cde_google_sheet_url = build_cde_url(schema=schema)

    # Ensure repo_root is on sys.path so that `import utils...` works when
    # executing this script as utils/generate_readme.py
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from utils.help_menus import (  # type: ignore
        get_app_intro_markdown,
        get_docs_intro_markdown,
        get_steps_table_markdown,
        get_two_types_of_issues_markdown,
    )

    intro_markdown = get_app_intro_markdown(
        cde_version=cde_version,
        cde_google_sheet_url=cde_google_sheet_url,
    )
    docs_intro_markdown = get_docs_intro_markdown()
    steps_table_markdown = get_steps_table_markdown(
        cde_version=cde_version,
        cde_google_sheet_url=cde_google_sheet_url,
    )
    two_types_of_issues_markdown = get_two_types_of_issues_markdown()

    update_readme(
        repo_root=repo_root,
        intro_markdown=intro_markdown,
        webapp_version=webapp_version,
    )
    update_docs_index(
        repo_root=repo_root,
        intro_markdown=docs_intro_markdown,
    )
    update_docs_steps_table(
        repo_root=repo_root,
        steps_table_markdown=steps_table_markdown,
    )
    update_docs_two_types_of_issues(
        repo_root=repo_root,
        two_types_of_issues_markdown=two_types_of_issues_markdown,
    )


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments for this script."""
    parser = argparse.ArgumentParser(
        prog="generate_readme",
        description=(
            "Sync app intro text across README.md and docs/index.md using "
            "resource/app_schema_{webapp_version}.json."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--webapp-version",
        required=True,
        help=(
            "Webapp version used to select resource/app_schema_{webapp_version}.json "
            "and update the README header (e.g. v0.9.2)."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point for the generate_readme CLI."""
    args = parse_args(argv)
    repository_root_path = Path(__file__).resolve().parent.parent
    repository_root_str = str(repository_root_path)
    sync_all(
        repo_root=repository_root_str,
        webapp_version=args.webapp_version,
    )
    print(
        f"README.md and docs/index.md successfully synced "
        f"for webapp_version={args.webapp_version}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
