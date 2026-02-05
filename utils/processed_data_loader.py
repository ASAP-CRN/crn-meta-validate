import io
import os
import re
import pandas as pd
from typing import Dict, Tuple, List, Any
import streamlit as st
from utils.find_missing_values import NULL_SENTINEL, normalize_null_like_dataframe
from utils.help_menus import inline_warning, get_current_function_name

class ProcessedDataLoader:
    """
    Loads processed files (dict or list) into DataFrames,
    handling encodings, bad lines, and fills out missing values with a string defined by NULL in _fillout_empty_cells()
    """
    def __init__(
        self,
        candidate_encodings: List[str] | None = None,
        default_separator: str = ",",
    ) -> None:
        self.candidate_encodings = candidate_encodings or ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
        self.default_separator = default_separator

    def load(
        self,
        processed_files: Dict[str, Any],
    ) -> Tuple[List[str], Dict[str, pd.DataFrame], Dict[str, List[str]], Dict[str, int]]:
        """
        Returns:
            table_names: list of sanitized table names in load order
            input_dataframes_dic: {table_name: DataFrame}
            file_warnings: {filename: [warning strings]}
            row_counts: {table_name: int}
        """
        table_names: List[str] = []
        input_dataframes_dic: Dict[str, pd.DataFrame] = {}
        file_warnings: Dict[str, List[str]] = {}
        row_counts: Dict[str, int] = {}

        # Keep a copy of each table before filling empty cells so downstream
        # UI (Step B) can preview and customize how missing values are handled.
        raw_tables_before_fill = st.session_state.get("raw_tables_before_fill", {})
        # Track the original separator used for each table so later downloads
        # (e.g., in Step 5) can preserve the user's delimiter choice.
        table_separators_by_table = st.session_state.get("table_separators_by_table", {})

        # Accept either a dict mapping filenames->payloads or a list of {name, bytes, delimiter}
        if isinstance(processed_files, dict):
            items_iter = processed_files.items()
        elif isinstance(processed_files, list):
            items_iter = [
                (item.get("name", f"table_{index}"), item)
                for index, item in enumerate(processed_files)
            ]
        else:
            raise TypeError("processed_files must be a dict or a list of {name, bytes, delimiter}")

        for filename, payload in items_iter:
            raw_bytes, separator = self._extract_bytes_and_separator(payload)
            table_name = self.sanitize_table_name(filename)
            # Remember which separator was actually used for this table
            table_separators_by_table[table_name] = separator
            warnings_for_file: List[str] = []

            table_df, used_encoding, used_engine, used_errors_mode = self._read_with_fallbacks(
                raw_bytes=raw_bytes,
                separator=separator,
            )

            if used_encoding not in ("utf-8", "utf-8-sig"):
                warnings_for_file.append(f"Loaded with fallback encoding '{used_encoding}'--consider resaving as UTF-8 to avoid character issues.")

            if used_engine == "python":
                warnings_for_file.append("Used the Python CSV engine for a tricky delimiter/format.")

            if used_errors_mode == "replace":
                warnings_for_file.append("Undecodable bytes were replaced during read.")

            # Store the raw table before filling out empty cells
            raw_tables_before_fill[table_name] = table_df.copy()

            # Normalize empty/textual-null cells to a single NA token
            table_df = self._fillout_empty_cells(table_df)

            # Store results for validation
            input_dataframes_dic[table_name] = table_df
            table_names.append(table_name)
            file_warnings[filename] = warnings_for_file

            try:
                row_counts[table_name] = int(len(table_df.index))
            except Exception:
                row_counts[table_name] = 0

        st.session_state["raw_tables_before_fill"] = raw_tables_before_fill
        st.session_state["table_separators_by_table"] = table_separators_by_table

        return table_names, input_dataframes_dic, file_warnings, row_counts

    # ---------- internals ----------

    def _fillout_empty_cells(self, table_df, na_token: str = NULL_SENTINEL):
        """Empty/NULL-like values to a single token so validation and exports are consistent.

        This delegates to utils.find_missing_values.normalize_null_like_dataframe()
        so that the same rules are used across the app.
        """
        return normalize_null_like_dataframe(table_df, sentinel=na_token)

    
    def _extract_bytes_and_separator(self, payload: Any) -> Tuple[bytes, str]:
        if isinstance(payload, dict):
            raw_bytes = payload.get("bytes", b"")
            separator = payload.get("delimiter", self.default_separator)
        else:
            raw_bytes = payload
            separator = self.default_separator
        if not isinstance(raw_bytes, (bytes, bytearray)):
            raise TypeError("processed_files payload must contain raw bytes.")
        return bytes(raw_bytes), separator

    def _read_with_fallbacks(
        self,
        raw_bytes: bytes,
        separator: str,
    ) -> Tuple[pd.DataFrame, str, str, str]:
        last_exception: Exception | None = None

        # Favor C engine for common separators; Python is more forgiving for exotic cases
        preferred_engine = "c" if separator in {",", "\t", ";", "|"} else "python"

        for encoding_name in self.candidate_encodings:
            try:
                table_df = pd.read_csv(
                    io.BytesIO(raw_bytes),
                    sep=separator,
                    dtype="string",
                    keep_default_na=False,
                    na_values=[],
                    on_bad_lines="skip",
                    encoding=encoding_name,
                    engine=preferred_engine,
                )
                return table_df, encoding_name, preferred_engine, "strict"
            except UnicodeDecodeError as decode_error:
                last_exception = decode_error
                continue
            except Exception as generic_error:
                last_exception = generic_error
                continue

        # Last resort: permissive read that won’t crash the app
        try:
            table_df = pd.read_csv(
                io.BytesIO(raw_bytes),
                sep=separator,
                dtype="string",
                keep_default_na=False,
                na_values=[],
                on_bad_lines="skip",
                encoding="latin-1",
                encoding_errors="replace",   # pandas >=1.5
                engine="python",
            )
            return table_df, "latin-1", "python", "replace"
        except Exception as final_error:
            warning_message = inline_warning(get_current_function_name(),
                                           f"Failed to read bytes with multiple encodings. "
                                           f"Last error was {type(last_exception).__name__}: {last_exception}"
                                           )
            st.warning(warning_message)
            raise RuntimeError(warning_message) from final_error

    def sanitize_table_name(self, filename: str) -> str:
        base = os.path.splitext(os.path.basename(filename))[0]
        # Normalize to a simple ASCII-ish identifier: spaces, punctuation -> underscores
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
        return normalized or "table"
