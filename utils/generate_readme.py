"""
Utility script to sync the README app-intro section with the shared intro
text defined in utils.help_menus.get_app_intro_markdown() and the values
from app_schema_{webapp_version}.json.

Usage (run from the repo root):
    python3 utils/generate_readme.py -v v1.0

This script tries two strategies to locate the intro block
inside README.md:

1) Preferred: markers
   If the README contains the markers:
       <!-- APP_INTRO_START -->
       <!-- APP_INTRO_END -->
   then everything between them will be replaced.

2) Fallback: heuristic
   If the markers are not present, the script looks for the text
   starting at "This app assists" and ending just after the bullet
   line that starts with "* Warnings".

If neither strategy works, the script raises RuntimeError.
"""

import argparse
import json
import os, sys
from pathlib import Path
from typing import Tuple
import streamlit as st

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


def find_marked_intro_block(readme_text: str) -> Tuple[int, int]:
    """Look for <!-- APP_INTRO_START --> ... <!-- APP_INTRO_END --> markers."""
    start_marker = "<!-- APP_INTRO_START -->"
    end_marker = "<!-- APP_INTRO_END -->"

    start_index = readme_text.find(start_marker)
    end_index = readme_text.find(end_marker)

    if start_index == -1 or end_index == -1:
        return -1, -1

    if end_index <= start_index:
        return -1, -1

    region_start = start_index + len(start_marker)
    region_end = end_index
    return region_start, region_end


def find_heuristic_intro_block(readme_text: str) -> Tuple[int, int]:
    """
    Fallback: locate block from 'This app assists' to line after '* Warnings'.
    """
    about_start_text = "This app assists"
    warnings_bullet = "* Warnings"

    about_start_index = readme_text.find(about_start_text)
    if about_start_index == -1:
        return -1, -1

    warnings_index = readme_text.find(warnings_bullet, about_start_index)
    if warnings_index == -1:
        return -1, -1

    newline_index = readme_text.find("\n", warnings_index)
    if newline_index == -1:
        region_end = len(readme_text)
    else:
        region_end = newline_index

    return about_start_index, region_end


def update_readme_intro(repo_root: str, webapp_version: str) -> None:
    """
    Replace the intro section in README.md with markdown generated from
    utils.help_menus.get_app_intro_markdown(), using values from
    app_schema_{webapp_version}.json.
    """
    schema_filename = f"app_schema_{webapp_version}.json"
    schema_path = os.path.join(repo_root, "resource", schema_filename)
    readme_path = os.path.join(repo_root,"README.md")

    if not os.path.exists(schema_path):
        raise RuntimeError(f"Schema file not found at: {schema_path}")

    if not os.path.exists(readme_path):
        raise RuntimeError(f"README not found at: {readme_path}")

    schema = load_schema(schema_path=schema_path)
    cde_version = schema["cde_definition"]["cde_version"]
    cde_google_sheet_url = build_cde_url(schema=schema)

    # Ensure repo_root is on sys.path so that `import utils...` works
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from utils.help_menus import get_app_intro_markdown  # type: ignore

    intro_markdown = (
        get_app_intro_markdown(
            cde_version=cde_version,
            cde_google_sheet_url=cde_google_sheet_url,
        ).rstrip()
        + "\n"
    )

    with open(readme_path, "r", encoding="utf-8") as readme_file:
        readme_text = readme_file.read()

    region_start, region_end = find_marked_intro_block(readme_text=readme_text)
    using_markers = region_start != -1 and region_end != -1

    if not using_markers:
        region_start, region_end = find_heuristic_intro_block(
            readme_text=readme_text,
        )

    if region_start == -1 or region_end == -1:
        raise RuntimeError(
            "Could not locate intro block in README.md. "
            "Consider adding markers <!-- APP_INTRO_START --> "
            "and <!-- APP_INTRO_END -->."
        )

    before_intro = readme_text[:region_start]
    after_intro = readme_text[region_end:]

    new_readme_text = (
        before_intro
        + "\n\n"
        + intro_markdown
        + "\n\n"
        + after_intro
    )

    with open(readme_path, "w", encoding="utf-8") as readme_file:
        readme_file.write(new_readme_text)


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments for this script."""
    parser = argparse.ArgumentParser(
        prog="generate_readme",
        description=(
            "Sync the README intro section with the shared app intro text "
            "using app_schema_{webapp_version}.json at the repo root."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--webapp-version",
        required=True,
        help=(
            "Webapp version string used to select the corresponding "
            "app_schema_{webapp_version}.json file at the repo root."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point for the generate_readme CLI."""
    args = parse_args(argv)
    repository_root_path = Path(__file__).resolve().parent.parent
    repository_root_str = str(repository_root_path)
    update_readme_intro(
        repo_root=repository_root_str,
        webapp_version=args.webapp_version,
    )
    print(
        "README.md successfully updated "
        f"for webapp_version={args.webapp_version}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
