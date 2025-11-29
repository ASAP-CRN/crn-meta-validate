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
import pandas as pd
import streamlit as st
import io
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass

LINES_TO_EVALUATE = 50 # Number of lines to read for delimiter detection
SUPPORTED_DELIMITERS = [",", ";", "\t", "|"] # Supported delimiters for detection

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
        Detect the delimiter used in a CSV-like file by scoring candidate delimiters.
        Returns (best_delimiter, confidence, preview_df).
        """
        if num_lines is None:
            num_lines = LINES_TO_EVALUATE

        # Read as text with robust decoding
        encodings_to_try = ("utf-8", "latin-1", "cp1252")
        decoded = None
        for enc in encodings_to_try:
            try:
                decoded = file_content.decode(enc) if isinstance(file_content, bytes) else file_content
                break
            except Exception:
                continue
        if decoded is None:
            decoded = (
                file_content.decode("utf-8", errors="ignore")
                if isinstance(file_content, bytes)
                else file_content
            )

        # Score delimiters by number of columns variance across first lines
        lines = decoded.splitlines()[: max(2, num_lines)]
        header = lines[0] if lines else ""
        delimiter_scores: Dict[str, Tuple[int, float]] = {}

        for delim in SUPPORTED_DELIMITERS:
            try:
                preview = pd.read_csv(io.StringIO(decoded), delimiter=delim, nrows=num_lines, dtype=str)
                cols = preview.shape[1]
                # Heuristic: prefer delimiters creating more columns; tie-breaker = ability to read >1 rows
                data_rows = max(0, len(preview) - 1)
                confidence = 0.5 + 0.5 * (1.0 if data_rows > 0 else 0.0)
                delimiter_scores[delim] = (cols, confidence)
            except Exception:
                delimiter_scores[delim] = (0, 0.0)

        best_delim = max(delimiter_scores.items(), key=lambda x: (x[1][1], x[1][0]))[0]
        confidence = delimiter_scores[best_delim][1]

        # Create preview dataframe
        try:
            preview_df = pd.read_csv(
                io.StringIO(decoded),
                delimiter=best_delim,
                nrows=num_lines,
                dtype=str,
            )
        except Exception:
            preview_df = None

        return best_delim, confidence, preview_df

    def convert_delimiter(self, file_content: bytes, from_delimiter: str, to_delimiter: str) -> bytes:
        """Convert content from one delimiter to another with robust decoding."""
        encodings_to_try = ("utf-8", "latin-1", "cp1252")

        for enc in encodings_to_try:
            try:
                text = file_content.decode(enc) if isinstance(file_content, bytes) else file_content
                df = pd.read_csv(io.StringIO(text), delimiter=from_delimiter, dtype=str)
                return df.to_csv(index=False, sep=to_delimiter).encode("utf-8")
            except Exception:
                continue

        text = (
            file_content.decode("utf-8", errors="ignore")
            if isinstance(file_content, bytes)
            else file_content
        )
        df = pd.read_csv(io.StringIO(text), delimiter=from_delimiter, dtype=str)
        return df.to_csv(index=False, sep=to_delimiter).encode("utf-8")

    def get_row_count(self, file_content: bytes, delimiter: str) -> int:
        """
        Get the number of data rows (excluding header), robust to encoding issues.
        """
        encodings_to_try = ("utf-8", "latin-1", "cp1252")
        for enc in encodings_to_try:
            try:
                text = file_content.decode(enc) if isinstance(file_content, bytes) else file_content
                df = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str)
                return max(0, len(df))
            except Exception:
                continue
        try:
            text = (
                file_content.decode("utf-8", errors="ignore")
                if isinstance(file_content, bytes)
                else file_content
            )
            df = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str)
            return max(0, len(df))
        except Exception:
            return 0

    # ---------- Validation & session-state support ----------

    def is_file_valid(self, preview_df: Optional[pd.DataFrame], row_count: int) -> bool:
        if preview_df is None:
            return False
        if row_count <= 0:
            return False
        return True

    def mark_file_as_invalid(self, filename: str, filesize: int):
        file_key = self.get_file_key(filename, filesize)
        invalid = st.session_state.invalid_files
        if isinstance(invalid, set):
            invalid.add(file_key)
        else:
            invalid[file_key] = True

    def is_file_invalid(self, filename: str, filesize: int) -> bool:
        file_key = self.get_file_key(filename, filesize)
        invalid = st.session_state.invalid_files
        if isinstance(invalid, set):
            return file_key in invalid
        return invalid.get(file_key, False)

    def show_invalid_file_error(
        self, filename: str, row_count: int, preview_df: Optional[pd.DataFrame], delimiter_name: str
    ):
        if row_count == 0:
            st.error(
                f"**{filename}** — file contains only headers with no data rows (detected {delimiter_name} delimiter). "
                "This file will be skipped during validation."
            )
        else:
            st.error(f"**{filename}** — Could not parse file.")

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
            st.dataframe(format_dataframe_for_preview(preview_df).head(10))

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
        Pre-pass over files to (a) detect delimiter, (b) compute row_count,
        (c) prompt/record decisions, (d) mark invalid. Returns True when all
        *valid* non-comma files have a recorded decision; otherwise False.
        """
        # Ensure state collections exist
        if "delimiter_decisions" not in st.session_state:
            st.session_state.delimiter_decisions = {}
        if "invalid_files" not in st.session_state:
            st.session_state.invalid_files = set()
        missing = 0
        for data_file in data_files:
            file_key = self.get_file_key(data_file.name, data_file.size)
            file_content = data_file.getvalue()

            delimiter, confidence, preview_df = self.detect_delimiter(file_content, data_file.name)
            delimiter_name = self.get_delimiter_name(delimiter)
            row_count = self.get_row_count(file_content, delimiter)

            # If invalid, mark and show error; skip decision
            if not self.is_file_valid(preview_df, row_count):
                self.mark_file_as_invalid(data_file.name, data_file.size)
                self.show_invalid_file_error(data_file.name, row_count, preview_df, delimiter_name)
                continue

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
