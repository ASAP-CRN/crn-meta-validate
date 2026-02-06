"""
Delimiter Handler Module

This module provides a comprehensive class for handling CSV file delimiter detection,
validation, conversion from supported delimiters to comma, and user interaction in Streamlit applications.

The delimiter handling includes:
- Detection of delimiters in uploaded files, with confidence scoring
- Files are read with their detected delimiters (comma, semicolon, tab, etc.)
- Validation of file contents, including checks for empty or invalid files, including those with column headers but no data rows
- User prompts for conversion decisions
- Session state management for user decisions

Author: Javier Diaz
"""

from __future__ import annotations

import csv
import io
import re
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from utils.help_menus import get_current_function_name, inline_error

LINES_TO_EVALUATE = 50  # Number of lines to read for delimiter detection
SUPPORTED_DELIMITERS = [",", ";", "\t", "|"]  # Supported delimiters for detection

# Keep encoding handling consistent across delimiter detection and full-file reads.
# Order matters:
# - utf-8-sig handles UTF-8 files that include a BOM (common with Excel exports)
# - latin-1 can decode any byte sequence, so it should be last to avoid masking problems
# - cp1252 is common on Windows for Western European languages
# This helps to handle special characters in data contributor last names.
DEFAULT_ENCODINGS_TO_TRY = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

@dataclass
class FileStatus:
    filename: str
    filesize: int
    is_invalid: bool = False


def format_dataframe_for_preview(dataframe: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Return a copy of *dataframe* suitable for Streamlit previews,
    where missing values appear as truly empty cells (no "None" strings).
    This helper is shared by multiple preview locations.
    """
    if dataframe is None:
        return None

    formatted = dataframe.copy()
    try:
        formatted = formatted.astype("string")
    except Exception:
        # If conversion fails, continue with the original dtypes
        pass

    formatted = formatted.fillna("")
    return formatted


def build_styled_preview_with_differences(
    original_df: Optional[pd.DataFrame],
    updated_df: Optional[pd.DataFrame],
    invalid_mask: Optional[pd.DataFrame] = None,
    app_schema: Optional[Dict] = None,
) -> Optional[pd.io.formats.style.Styler]:
    """
    Return a pandas Styler object for *updated_df* suitable for use with ``st.dataframe``,
    highlighting:
      * cells that differ from *original_df* in green, and
      * cells that are invalid w.r.t. CDE Validation/FillNull in orange.
    When a cell is both changed and invalid, the invalid (orange) color wins.
    """
    formatted_updated = format_dataframe_for_preview(updated_df)
    if formatted_updated is None:
        return None

    formatted_original = format_dataframe_for_preview(original_df)
    if formatted_original is None:
        return formatted_updated.style

    # Align original to updated so that the comparison is on the same index/columns
    aligned_original = formatted_original.reindex_like(formatted_updated)

    difference_mask = aligned_original.ne(formatted_updated)

    # Align invalid mask, if provided
    if invalid_mask is not None:
        aligned_invalid = invalid_mask.reindex_like(formatted_updated)
        # Convert to a plain boolean array, treating NA as False
        invalid_values = aligned_invalid.to_numpy(dtype=bool, na_value=False)
    else:
        invalid_values = None

    def _highlight_differences(dataframe: pd.DataFrame) -> pd.DataFrame:
        base = np.full(dataframe.shape, "", dtype=object)

        # First, mark invalid cells in orange
        if invalid_values is not None:
            base = np.where(invalid_values, f"color: {app_schema['preview_invalid_cde_color']}", base)

        # Then, mark changed-but-valid cells in green
        if invalid_values is not None:
            diff_only = difference_mask & ~invalid_values
        else:
            diff_only = difference_mask

        # Ensure there are no ambiguous pd.NA values in the mask
        diff_only_array = diff_only.to_numpy(dtype=bool, na_value=False)
        base = np.where(diff_only_array, f"color: {app_schema['preview_fillout_color']}", base)
        return pd.DataFrame(base, index=dataframe.index, columns=dataframe.columns)

    return formatted_updated.style.apply(_highlight_differences, axis=None)



class DelimiterHandler:
    """
    Handles detection and conversion of delimiters and keeps per-file decisions/status.
    """
    def __init__(self):
        """Initialize the DelimiterHandler with session state."""
        # Ensure both keys exist in session_state and have valid types
        if 'delimiter_decisions' not in st.session_state or not isinstance(st.session_state.delimiter_decisions, dict):
            st.session_state.delimiter_decisions = {}
        if 'invalid_files' not in st.session_state or not isinstance(st.session_state.invalid_files, (dict, set)):
            st.session_state.invalid_files = {}

    @staticmethod
    def decode_bytes_with_fallbacks(file_content: bytes) -> Tuple[str, str, str]:
        """Decode *file_content* into text using a consistent set of candidate encodings.

        Returns:
            decoded_text: The decoded string.
            used_encoding: The encoding name that succeeded.
            used_errors_mode: "strict" if decoded without substitution, otherwise "ignore".

        Note: We avoid "replace" here for delimiter detection/structure checks because it can
        silently mutate separators. "ignore" is used only as a last resort.
        """
        if not isinstance(file_content, (bytes, bytearray)):
            return str(file_content), "text", "strict"

        for encoding_name in DEFAULT_ENCODINGS_TO_TRY:
            try:
                decoded_text = bytes(file_content).decode(encoding_name)
                return decoded_text, encoding_name, "strict"
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        decoded_text = bytes(file_content).decode("utf-8", errors="ignore")
        return decoded_text, "utf-8", "ignore"

    # ---------- Helpers for session keys / labels ----------

    def get_file_key(self, filename: str, filesize: int) -> str:
        return f"{filename}_{filesize}"

    def get_delimiter_name(self, delimiter: str) -> str:
        names = {
            ",": "comma",
            ";": "semicolon",
            "\t": "tab", 
            "|": "pipe"
            }
        return names.get(delimiter, repr(delimiter))

    # ---------- Detection / conversion ----------
    def detect_delimiter(
        self, file_content: bytes, filename: str, num_lines: int = None
    ) -> Tuple[str, float, Optional[pd.DataFrame]]:
        """
        Detect the delimiter used in a CSV-like file using line-level statistics.

        This avoids false positives where an *incorrect* delimiter appears to "work"
        simply because pandas can read the entire file as a single column (e.g., picking ';'
        for a malformed comma-delimited file).

        Returns (best_delimiter, confidence, preview_df).
        """
        if num_lines is None:
            num_lines = LINES_TO_EVALUATE

        decoded, _used_encoding, _used_errors_mode = self.decode_bytes_with_fallbacks(file_content)

        # Keep only the first N non-empty lines for scoring
        lines = [line for line in decoded.splitlines() if line.strip()]
        if not lines:
            return ",", 0.0, None

        header_line = lines[0]
        candidate_lines = lines[: max(2, min(len(lines), num_lines))]

        # Score delimiters by:
        # - presence in header (hard requirement)
        # - typical count per line (median)
        # - consistency across lines (fraction matching median)
        # - preference for producing >1 column in header
        delimiter_scores: Dict[str, float] = {}

        for delim in SUPPORTED_DELIMITERS:
            if delim not in header_line:
                # If the delimiter is not in the header, disqualify it.
                delimiter_scores[delim] = -1.0
                continue

            counts = [line.count(delim) for line in candidate_lines]
            if not counts:
                delimiter_scores[delim] = -1.0
                continue

            median_count = statistics.median(counts)
            if median_count <= 0:
                delimiter_scores[delim] = -1.0
                continue

            # Consistency: how many lines match the median delimiter count?
            matches = sum(1 for count in counts if count == median_count)
            consistency = matches / float(len(counts))

            # Column estimate from header line
            est_cols = header_line.count(delim) + 1
            if est_cols <= 1:
                delimiter_scores[delim] = -1.0
                continue

            # Weighted score: consistency dominates; higher median_count slightly preferred
            delimiter_scores[delim] = (consistency * 100.0) + float(median_count)

        # Choose best delimiter; fall back to comma
        best_delim = max(delimiter_scores, key=delimiter_scores.get)
        best_score = delimiter_scores.get(best_delim, -1.0)

        if best_score < 0:
            best_delim = ","
            confidence = 0.0
        else:
            # Map (roughly) to 0-100 confidence
            confidence = min(100.0, max(0.0, best_score))

        # Build a preview dataframe using a forgiving read so malformed rows do not zero-out detection.
        preview_df: Optional[pd.DataFrame] = None
        try:
            preview_df = pd.read_csv(
                io.StringIO(decoded),
                sep=best_delim,
                dtype=str,
                engine="python",
                on_bad_lines="skip",
                nrows=20,
            )
            preview_df = format_dataframe_for_preview(preview_df)
        except Exception:
            preview_df = None

        return best_delim, float(confidence), preview_df

    def get_row_count(self, file_content: bytes, delimiter: str) -> int:
        """
        Return the number of data rows in the file for the provided delimiter.

        Important: some real-world CSVs are malformed (rows with extra delimiters).
        We therefore attempt a strict parse first and, on failure, fall back to a
        forgiving parse that skips bad lines.

        Returns:
            >= 0 : number of parsed data rows
            -1   : file appears to contain data rows, but parsing failed even with fallback
        """
        if not file_content:
            return 0

        decoded, _used_encoding, _used_errors_mode = self.decode_bytes_with_fallbacks(file_content)

        non_empty_lines = [line for line in decoded.splitlines() if line.strip()]
        if len(non_empty_lines) <= 1:
            return 0

        # First attempt: strict parse
        try:
            df = pd.read_csv(io.StringIO(decoded), sep=delimiter, dtype=str)
            return max(0, len(df))
        except Exception:
            pass

        # Second attempt: forgiving parse (skip bad lines)
        try:
            df = pd.read_csv(
                io.StringIO(decoded),
                sep=delimiter,
                dtype=str,
                engine="python",
                on_bad_lines="skip",
            )
            return max(0, len(df))
        except Exception:
            # There are data-looking lines, but parsing failed.
            return -1

    def validate_and_report_structure(self, file_content: bytes, delimiter: str, filename: str) -> bool:
        """
        Validate that all rows have the same number of fields as the header.

        We attempt a strict pandas parse first (fast, uses C engine). If pandas raises a ParserError like:
            "Expected 24 fields in line 4, saw 25"
        then we parse the message and emit a targeted Streamlit error.

        Returns:
            True  : structure appears consistent (or at least parseable)
            False : structure mismatch detected (first offending line reported)
        """
        decoded, _used_encoding, _used_errors_mode = self.decode_bytes_with_fallbacks(file_content)

        try:
            # Strict read: error on any malformed row.
            pd.read_csv(io.StringIO(decoded), sep=delimiter, dtype=str)
            return True
        except pd.errors.ParserError as exc:
            message = str(exc)
            match = re.search(r"Expected\s+(\d+)\s+fields\s+in\s+line\s+(\d+),\s+saw\s+(\d+)", message)
            if match:
                expected_fields = int(match.group(1))
                line_number = int(match.group(2))
                saw_fields = int(match.group(3))
                error_message = inline_error(get_current_function_name(),
                                             f"File **{filename}** has {saw_fields} fields in row {line_number}, "
                                             f"but {expected_fields} fields in header."
                                             )
                st.error(error_message)
                return False

            # Fallback: compute the first mismatch using the csv module for clearer reporting.
            reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                error_message = inline_error(get_current_function_name(), 
                                             f"File **{filename}** appears to be empty.")
                st.error(error_message)
                return False

            header_fields = len(header)
            for row_index_1based, row in enumerate(reader, start=2):
                if not row:
                    continue
                if len(row) != header_fields:
                    error_message = inline_error(get_current_function_name(),
                                                 f"File **{filename}** has {len(row)} fields in row {row_index_1based}, "
                                                 f"but {header_fields} fields in header."
                                                 )
                    st.error(error_message)
                    return False

            # If we cannot locate it, emit the original parser error to help debugging.
            error_message = inline_error(get_current_function_name(),
                                         f"File **{filename}** could not be parsed: {message}")
            st.error(error_message)
            return False

    def is_file_invalid(self, filename: str, filesize: int) -> bool:
        file_key = self.get_file_key(filename, filesize)
        invalid = st.session_state.invalid_files
        if isinstance(invalid, set):
            return file_key in invalid
        return invalid.get(file_key, False)
    
    def is_file_valid(self, preview_df: Optional[pd.DataFrame], row_count: int) -> bool:
        """Return True if the file should be treated as valid for validation purposes."""
        if row_count == 0:
            return False
        # row_count < 0 means "appears to contain data, but parsing had issues" -> treat as valid
        if preview_df is None:
            return row_count != 0
        return True

    def show_invalid_file_error(
        self, filename: str, row_count: int, preview_df: Optional[pd.DataFrame], delimiter_name: str
    ):
        if row_count == 0:
            error_message = inline_error(get_current_function_name(),
                                         f"File **{filename}** contains only headers with no data rows (detected **{delimiter_name}** delimiter). "
                                         f"This file will be skipped during validation")
            st.error(error_message)
        elif row_count < 0:
            error_message = inline_error(get_current_function_name(),
                                         f"File **{filename}** appears to contain data rows, but one or more rows could not be parsed "
                                         f"(detected **{delimiter_name}** delimiter). This file will be skipped during validation."
                                         )
            st.error(error_message)
        else:
            error_message = inline_error(get_current_function_name(),
                                         f"File **{filename}** — Could not parse file."
                                         )
            st.error(error_message)

    def show_conversion_prompt(
        self,
        filename: str,
        row_count: int,
        delimiter_name: str,
        confidence: float,
        preview_df: Optional[pd.DataFrame],
        file_key: str,
    ):
        st.info(f"**{filename}** ({row_count} rows) — file detected **{delimiter_name}** delimited (confidence {confidence:.0%}).")
        if preview_df is not None:
            rows_to_show = st.session_state.get('preview_max_rows', 10)
            preview_df_formatted = format_dataframe_for_preview(preview_df)
            st.dataframe(preview_df_formatted.head(rows_to_show))

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"Yes, convert {filename} to comma", key=f"convert_{file_key}"):
                st.session_state.delimiter_decisions[file_key] = {"action": "convert"}
                st.rerun()
        with col2:
            if st.button(f"No, keep original {filename}", key=f"keep_{file_key}"):
                st.session_state.delimiter_decisions[file_key] = {"action": "keep"}
                st.rerun()

    def get_valid_file_names(self, data_files: List[Any]) -> List[Any]:
        return [
            f for f in data_files if not self.is_file_invalid(f.name, f.size)
        ]

    def get_invalid_file_names(self, data_files: List[Any]) -> List[Any]:
        return [
            f for f in data_files if self.is_file_invalid(f.name, f.size)
        ]

    def clear_decisions(self):
        st.session_state.delimiter_decisions.clear()
        st.session_state.invalid_files.clear()

    def get_file_status_display(self, data_files: List[Any]) -> str:
        valid = len(self.get_valid_file_names(data_files))
        invalid = len(self.get_invalid_file_names(data_files))
        decided = len(st.session_state.get("delimiter_decisions", {}))
        return f"{valid} valid, {invalid} invalid, {decided} decisions recorded"
    
    def check_delimiter_decisions(self, data_files: List[Any]) -> bool:
        """
        Pre-pass over files to:
        (a) detect delimiter
        (b) compute row_count (with malformed-row tolerance)
        (c) mark invalid (truly empty / header-only)
        (d) prompt for conversion decisions for non-comma files

        Returns True when all *valid* non-comma files have a recorded decision;
        otherwise False (the caller should st.stop()).
        """
        if "delimiter_decisions" not in st.session_state:
            st.session_state.delimiter_decisions = {}
        if "invalid_files" not in st.session_state:
            st.session_state.invalid_files = set()

        missing = 0

        for data_file in data_files:
            file_key = self.get_file_key(data_file.name, data_file.size)

            try:
                file_content = data_file.getvalue()
            except Exception:
                file_content = data_file.read()

            if not file_content:
                # Treat as invalid/empty
                if isinstance(st.session_state.invalid_files, set):
                    st.session_state.invalid_files.add(file_key)
                else:
                    st.session_state.invalid_files[file_key] = True
                self.show_invalid_file_error(
                    filename=data_file.name,
                    row_count=0,
                    preview_df=None,
                    delimiter_name="unknown",
                )
                continue

            delimiter, confidence, preview_df = self.detect_delimiter(file_content, data_file.name)
            delimiter_name = self.get_delimiter_name(delimiter)
            row_count = self.get_row_count(file_content, delimiter)
            # Structural validation: catch malformed rows early so the app does not crash later.
            if not self.validate_and_report_structure(file_content, delimiter, data_file.name):
                if isinstance(st.session_state.invalid_files, set):
                    st.session_state.invalid_files.add(file_key)
                else:
                    st.session_state.invalid_files[file_key] = True
                continue

            # Invalid if truly header-only (0). If -1, we warn but do not drop.
            if row_count == 0:
                if isinstance(st.session_state.invalid_files, set):
                    st.session_state.invalid_files.add(file_key)
                else:
                    st.session_state.invalid_files[file_key] = True
                self.show_invalid_file_error(
                    filename=data_file.name,
                    row_count=row_count,
                    preview_df=preview_df,
                    delimiter_name=delimiter_name,
                )
                continue

            # Non-fatal parsing issue
            if row_count < 0:
                self.show_invalid_file_error(
                    filename=data_file.name,
                    row_count=row_count,
                    preview_df=preview_df,
                    delimiter_name=delimiter_name,
                )

            # For valid files: only prompt if not comma and no decision yet
            if delimiter != "," and file_key not in st.session_state.delimiter_decisions:
                self.show_conversion_prompt(
                    filename=data_file.name,
                    row_count=row_count,
                    delimiter_name=delimiter_name,
                    confidence=confidence,
                    preview_df=preview_df,
                    file_key=file_key,
                )
                missing += 1

        return missing == 0
    
    def apply_decisions(self, data_files):
        """Apply user's delimiter decisions and return a list of {name, bytes}. Also store in session."""
        processed = []
        decisions = st.session_state.get("delimiter_decisions", {})
        # Iterate over uploaded files in order; decisions are keyed by file_key
        for f in data_files:
            file_key = self.get_file_key(f.name, f.size)
            decision = decisions.get(file_key)
            # Get raw bytes
            try:
                raw = f.getvalue()
            except Exception:
                raw = f.read()
            if not raw:
                continue
            # Determine action
            action = None
            detected_char = None
            if isinstance(decision, dict):
                action = decision.get("action") or decision.get("decision")
                detected_char = decision.get("detected") or decision.get("detected_char")
            elif isinstance(decision, str):
                action = decision
            else:
                # default: keep if no decision
                action = "keep"
            # If converting, figure out delimiter char
            # Ensure detected_char is set for the keep path
            if not detected_char:
                try:
                    _fallback_delim, _, _ = self.detect_delimiter(raw, f.name)
                    detected_char = _fallback_delim
                except Exception:
                    detected_char = ";"  # reasonable default for European CSVs
            # If converting, figure out delimiter char
            if action == "convert":
                if not detected_char or len(str(detected_char)) > 1:
                    delim, _, _ = self.detect_delimiter(raw, f.name)
                else:
                    delim = detected_char
                try:
                    df = pd.read_csv(io.BytesIO(raw), dtype=str, sep=delim)
                    buf = io.BytesIO()
                    df.to_csv(buf, index=False)
                    processed.append({"name": f.name, "bytes": buf.getvalue(), "delimiter": ","})
                except Exception as e:
                    st.warning(f"Could not convert '{f.name}': {e}. Keeping original bytes.")
                    processed.append({"name": f.name, "bytes": raw, "delimiter": detected_char})
            else:
                processed.append({"name": f.name, "bytes": raw, "delimiter": detected_char})
        st.session_state['files_ready_for_validation'] = processed
        return processed

# ---------- End of DelimiterHandler class ----------
