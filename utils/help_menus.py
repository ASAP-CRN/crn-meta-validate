import re
import streamlit as st
import ast
import html
from typing import Any, Callable, Dict, List, Tuple

def ensure_step1_other_options(
    species_options: List[str],
    sample_source_options: List[str],
    assay_type_options: List[str],
    assay_label_to_key: Dict[str, str],
    assay_keys: set[str],
) -> Tuple[List[str], List[str], List[str], Dict[str, str], set[str]]:
    """Ensure that Step 1 drop-downs include an "Other" option.

    Returns the (possibly updated) containers to make usage explicit at call sites.
    """
    if "Other" not in species_options:
        species_options.append("Other")
    if "Other" not in sample_source_options:
        sample_source_options.append("Other")
    if "Other" not in assay_type_options:
        assay_type_options.append("Other")

    if "Other" not in assay_label_to_key:
        assay_label_to_key["Other"] = "other"
    assay_keys.add("other")

    return (
        species_options,
        sample_source_options,
        assay_type_options,
        assay_label_to_key,
        assay_keys,
    )

def render_step1_selectbox_with_other_text(
    *,
    heading_html: str,
    selectbox_label: str,
    selectbox_options: List[str],
    selectbox_key: str,
    selectbox_placeholder: str,
    other_text_label: str,
    other_text_key: str,
) -> Tuple[str | None, str]:
    """Render a Step 1 selectbox that conditionally reveals an "Other" free-text input.

    The free-text value is stored in st.session_state[other_text_key]. If the selectbox
    is not set to "Other", the stored value is cleared.
    """
    st.markdown(heading_html, unsafe_allow_html=True)
    selected_value = st.selectbox(
        selectbox_label,
        selectbox_options,
        label_visibility="collapsed",
        index=None,
        placeholder=selectbox_placeholder,
        key=selectbox_key,
    )

    other_text_value = ""
    if selected_value == "Other":
        other_text_value = st.text_area(
            other_text_label,
            key=other_text_key,
            height=15,
            label_visibility="collapsed",
            placeholder=f"{other_text_label} here…",
        )
    else:
        st.session_state[other_text_key] = ""

    return selected_value, str(other_text_value or "")


def build_step1_report_markdown(step1_other_fields: Dict[str, str]) -> str:
    """Build the step1_report.md content for Step 1 "Other" free-text entries."""
    report_lines: List[str] = [
        "# General report",
        "",
        "## Step 1: Free-text entries for 'Other' selections",
        "",
    ]

    species_other_text = str(step1_other_fields.get("species_other", "") or "").strip()
    sample_source_other_text = str(step1_other_fields.get("sample_source_other", "") or "").strip()
    assay_other_text = str(step1_other_fields.get("assay_type_other", "") or "").strip()

    other_entries_present = False
    if species_other_text:
        other_entries_present = True
        report_lines.append(f"- **Dataset species (Other):** {species_other_text}")
    if sample_source_other_text:
        other_entries_present = True
        report_lines.append(f"- **Sample source (Other):** {sample_source_other_text}")
    if assay_other_text:
        other_entries_present = True
        report_lines.append(f"- **Assay type (Other):** {assay_other_text}")

    if not other_entries_present:
        report_lines.append("_No 'Other' free-text entries were provided in Step 1._")

    report_lines.append("")
    return "\n".join(report_lines)


def build_hover_text_from_description(description_text: str) -> str:
    """Return HTML-escaped hover text built from a column description.
    This keeps tooltip construction consistent across the app.
    """
    description_text_stripped = (description_text or "").strip()
    hover_parts: List[str] = []
    if description_text_stripped:
        hover_parts.append(description_text_stripped)
    hover_text = " | ".join(hover_parts)
    return html.escape(hover_text, quote=True)

def build_free_text_header_markdown(column_name: str, hover_text: str) -> None:
    """Render the free-text comment box header markdown for a given column."""
    free_text_header_markdown = f"""
    <div style="font-size:16px;">
        Record comments on column
        <span class="tooltip-wrapper">
            <span class="missing-hover">{column_name}</span>
            <span class="tooltip-text">{hover_text}</span>
        </span> (optional):
    </div>
    """
    return free_text_header_markdown

def get_app_intro_markdown(cde_version: str, cde_google_sheet_url: str) -> str:
    """Return the main app introduction text shared between the UI and docs."""
    return f"""This app assists data contributors to QC their metadata tables in comma-delimited format (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.

We do this in five steps:     
**Step 1. Indicate your Dataset type:** the app will determine expected CSV files and columns.     
**Step 2. Download template files:** a left-side bar will appear indicating expected files and providing file templates.     
**Step 3. Fill out and upload files:** offline, fill out files with your metadata and upload them via the Drag & drop box or Browse button.     
**Step 4. Fix common issues:** follow app instructions to fix common issues (e.g. non-comma delimiters and missing values).     
**Step 5. CDE validation:** the app reports missing columns and value mismatches vs. the [ASAP CRN controlled vocabularies (CDE) {cde_version}]({cde_google_sheet_url}).

Two types of issues will be reported:     
**Errors (❌):**  must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.     
**Warnings (⚠️):** recommended to be fixed before uploading, but not required.     

Free text boxes allow users to record per-column comments to provide context to data curators during review.
"""

def render_app_intro(webapp_version: str, cde_version: str, cde_google_sheet_url: str) -> None:
    """Render the main app introduction at the top of the UI."""
    import streamlit as st  # local import to avoid cycles during tooling
    st.markdown(
        f'<p class="big-font">ASAP CRN metadata quality control (QC) app {webapp_version}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        get_app_intro_markdown(
            cde_version=cde_version,
            cde_google_sheet_url=cde_google_sheet_url,
        )
    )


class CustomMenu:
    """
    A custom menu component that replaces Streamlit's default kebab menu.
    Displays only a Help link in a modern, minimalist style.

    Also hides the sidebar collapse button (<<) to prevent users from hiding the sidebar.
    Because Streamlit does not provide direct API to customize the menu and hiding the sidebar was causing issues
    with not being able to bring the sidebar back easily.
    """
    
    def __init__(self, help_url: str):
        """
        Initialize the CustomMenu.
        
        Args:
            help_url: URL for the help/documentation page
        """
        self.help_url = help_url
    
    def hide_default_menu(self):
        """Hide the default Streamlit kebab menu and customize sidebar."""
        st.markdown(
            """
            <style>
            /* Hide ONLY the kebab menu button, keep everything else */
            [data-testid="stMainMenu"] {
                display: none !important;
            }
            
            /* Hide the Deploy button */
            [data-testid="stToolbar"] {
                display: none !important;
            }
            
            /* Hide the sidebar collapse button (<<) to prevent users from hiding sidebar */
            button[kind="header"][data-testid="baseButton-header"] {
                display: none !important;
            }
            
            /* Alternative selector for collapse button */
            [data-testid="stSidebarCollapseButton"] {
                display: none !important;
            }
            
            /* Also hide by aria-label */
            button[aria-label="Close sidebar"] {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    
    def render(self):
        """Render the custom menu in the top-right corner."""
        # Hide the default menu
        self.hide_default_menu()
        
        # Inject custom Help link using Streamlit's markdown method
        st.markdown(
            f"""
            <style>
            /* Position container in top-right, below header */
            .custom-menu-container {{
                position: fixed;
                top: 3.5rem;
                right: 1rem;
                z-index: 999999;
            }}
            
            /* Help link styling - simple and modern */
            .help-link {{
                color: #31333F;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 400;
                padding: 0.5rem 1rem;
                border-radius: 0.375rem;
                transition: background-color 0.2s ease;
                background-color: white;
                border: 1px solid #e6e6e6;
                display: inline-block;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }}
            
            .help-link:hover {{
                background-color: #f0f2f6;
                text-decoration: none;
            }}
            </style>
            
            <div class="custom-menu-container">
                <a href="{self.help_url}" target="_blank" class="help-link">Help</a>
            </div>
            """,
            unsafe_allow_html=True
        )

def parse_fillnull_values(fillnull_text: str) -> List[str]:
    """Parse the FillNull field from the CDE into a list of string values."""
    fillnull_values: List[str] = []
    if not fillnull_text:
        return fillnull_values

    try:
        parsed_fillnull = ast.literal_eval(fillnull_text)
        if isinstance(parsed_fillnull, (list, tuple)):
            fillnull_values = [str(value) for value in parsed_fillnull]
        else:
            fillnull_values = [str(parsed_fillnull)]
    except Exception:
        fillnull_values = [fillnull_text]

    return fillnull_values


def render_missing_values_section(
    section_kind: str,  # "required" or "optional"
    selected_table_name: str,
    fields: List[str],
    selected_raw_df: Any,
    compute_missing_mask: Callable[[Any], Any],
    cde_meta_by_field: Dict[str, Dict[str, str]],
    column_choices: Dict[str, str],
    enum_choice: Dict[str, str] | None = None,
    has_required_columns_with_missing: bool = False,
) -> List[Tuple[str, int]]:
    """Render the missing-values UI for required or optional columns.
    Returns a list of (field_name, missing_count) for columns that had missing values.
    """
    columns_with_missing: List[Tuple[str, int]] = []

    # Deduplicate field names while preserving order, and skip columns not in the DataFrame
    seen_field_names: set[str] = set()
    for field_name in fields:
        if field_name in seen_field_names:
            continue
        seen_field_names.add(field_name)

        if field_name not in selected_raw_df.columns:
            continue

        column_series = selected_raw_df[field_name]
        missing_mask = compute_missing_mask(column_series)
        missing_count = int(missing_mask.sum())
        if missing_count > 0:
            columns_with_missing.append((field_name, missing_count))

    if len(columns_with_missing) == 0:
        return columns_with_missing

    # Horizontal rule between required and optional sections
    if section_kind == "optional" and has_required_columns_with_missing:
        st.markdown("---")

    # Section header
    if section_kind == "required":
        st.markdown(f"#### Missing values in _{selected_table_name}_ required columns")
    else:
        st.markdown(f"#### Missing values in _{selected_table_name}_ optional columns")

    for field_index, (field_name, missing_count) in enumerate(columns_with_missing):
        field_meta = cde_meta_by_field.get(field_name, {})
        description_text = str(field_meta.get("Description", "") or "").strip()
        datatype_text = str(field_meta.get("DataType", "") or "").strip()
        validation_text = str(field_meta.get("Validation", "") or "").strip()
        fillnull_text = str(field_meta.get("FillNull", "") or "").strip()
        datatype_lower = datatype_text.lower()
        hover_text_escaped = build_hover_text_from_description(description_text)
        free_text_markdown = build_free_text_header_markdown(field_name, hover_text_escaped)

        # Build FillNull-driven options, with DataType fallbacks
        fillnull_values = parse_fillnull_values(fillnull_text)

        option_labels: List[str] = []
        if fillnull_values:
            for fill_value in fillnull_values:
                option_labels.append(f'Fill out with "{fill_value}"')
        else:
            st.error(
                "ERROR!!! No FillNull values were found for "
                f"field '{field_name}' in table '{selected_table_name}' "
                f"(section: {section_kind}). Please ensure the CDE FillNull "
                "column is complete and reload the app.",
            )
            st.stop()

        existing_choice = column_choices.get(field_name, option_labels[0])
        try:
            default_index = option_labels.index(existing_choice)
        except ValueError:
            default_index = 0

        # Card styling (required vs optional)
        block_class = "missing-block-required" if section_kind == "required" else "missing-block-optional"
        severity_icon = "❌" if section_kind == "required" else "⚠️"
        section_label = "Required" if section_kind == "required" else "Optional"

        st.markdown(
            f"""
            <div class="missing-block {block_class}">
                <div class="missing-block-title">
                    {severity_icon} <strong>&nbsp;{section_label}</strong> column
                    <span class="tooltip-wrapper">
                        <span class="missing-hover"><strong>{field_name}</strong></span>
                        <span class="tooltip-text">{hover_text_escaped}</span>
                    </span>
                    has {missing_count} empty values. Expect data type: {datatype_text}.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fillout_tools_column, comments_column = st.columns(2)
        with fillout_tools_column:
            # Required vs. optional layout for enum dropdown
            is_enum_required_column = (
                section_kind == "required"
                and "enum" in datatype_lower
                and bool(validation_text)
            )
            
            # Initialize variables for enum dropdown handling
            enum_key = None
            placeholder_label = "Select an option"
            
            # CRITICAL: Check if we need to reset the dropdown BEFORE creating widgets
            # This must happen before the selectbox is instantiated
            if is_enum_required_column:
                enum_key = f"mv_enum_required_{selected_table_name}_{field_name}_{field_index}"
                radio_key = f"mv_radio_{section_kind}_{selected_table_name}_{field_name}_{field_index}"
                last_interaction_key = f"last_interaction_{selected_table_name}_{field_name}_{field_index}"
                
                # Only reset dropdown if radio button was the LAST thing changed
                if enum_choice is not None:
                    current_enum_value = enum_choice.get(field_name, "")
                    last_interaction = st.session_state.get(last_interaction_key, None)
                    
                    # Reset dropdown only if:
                    # 1. A dropdown value was previously set
                    # 2. The last interaction was with the radio button (not dropdown)
                    if current_enum_value and last_interaction == "radio":
                        # Radio was clicked after dropdown - reset dropdown
                        enum_choice[field_name] = ""
                        st.session_state[enum_key] = placeholder_label
                        # Clear the interaction tracker
                        st.session_state[last_interaction_key] = None

            if is_enum_required_column:
                if enum_choice is None:
                    enum_choice = {}

                existing_enum_choice = enum_choice.get(field_name, "")

                validation_values: List[str] = []
                try:
                    parsed_validation = ast.literal_eval(validation_text)
                    if isinstance(parsed_validation, (list, tuple)):
                        validation_values = [str(value) for value in parsed_validation]
                    else:
                        validation_values = [str(parsed_validation)]
                except Exception:
                    validation_values = [validation_text]

                if validation_values:
                    full_options = [placeholder_label] + validation_values

                    if existing_enum_choice and existing_enum_choice not in full_options:
                        full_options.append(existing_enum_choice)

                    if existing_enum_choice and existing_enum_choice in full_options:
                        default_enum_index = full_options.index(existing_enum_choice)
                    else:
                        default_enum_index = 0

                    st.markdown(
                        f"""
                        <div style="font-size:16px;">
                            Use a controlled vocabulary to fill out column
                            <span class="tooltip-wrapper">
                                <span class="missing-hover">{field_name}</span>
                                <span class="tooltip-text">{hover_text_escaped}</span>
                            </span>:
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    selected_enum_value = st.selectbox(
                        "Dropdown fill-null options",
                        full_options,
                        label_visibility="collapsed",
                        index=None,
                        placeholder="Type to search controlled vocabulary…",
                    )

                    # Track dropdown interaction
                    last_interaction_key = f"last_interaction_{selected_table_name}_{field_name}_{field_index}"
                    prev_dropdown_key = f"prev_dropdown_{selected_table_name}_{field_name}_{field_index}"
                    prev_dropdown_value = st.session_state.get(prev_dropdown_key, None)
                    
                    # Check if dropdown value actually changed
                    if prev_dropdown_value != selected_enum_value:
                        # Dropdown was just changed - mark it as last interaction
                        if selected_enum_value != placeholder_label:
                            st.session_state[last_interaction_key] = "dropdown"
                        st.session_state[prev_dropdown_key] = selected_enum_value

                    if selected_enum_value != placeholder_label:
                        # User explicitly chose a controlled vocabulary value; override choices.
                        enum_choice[field_name] = selected_enum_value
                    else:
                        # Helper text selected; clear the enum choice to allow radio button to take effect.
                        enum_choice[field_name] = ""
                else:
                    enum_choice[field_name] = existing_enum_choice
            elif section_kind == "required":
                # Non-enum required column: maintain key in enum_choice without a value override.
                if enum_choice is not None:
                    existing_enum_choice = enum_choice.get(field_name, "")
                    enum_choice[field_name] = existing_enum_choice

            # Dotted line '---OR---' separator for Enum required columns
            if is_enum_required_column:
                st.markdown(
                    """
                    <div style="
                        display: flex;
                        align-items: center;
                        text-align: center;
                        margin: 0.5rem 0;
                    ">
                        <div style="flex: 1; border-top: 1px dotted #cccccc;"></div>
                        <span style="margin: 0 0.5rem; font-weight: 600; color: #666;">
                            OR
                        </span>
                        <div style="flex: 1; border-top: 1px dotted #cccccc;"></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Radio buttons for generic FillNull options
            radio_key_prefix = f"mv_radio_{section_kind}"
            radio_key = f"{radio_key_prefix}_{selected_table_name}_{field_name}_{field_index}"

            st.markdown(
                f"""
                <div style="font-size:16px;">
                    Choose a generic value to fill out column 
                    <span class="tooltip-wrapper">
                        <span class="missing-hover">{field_name}</span>
                        <span class="tooltip-text">{hover_text_escaped}</span>
                    </span>:
                </div>
                """,
                unsafe_allow_html=True,
            )

            user_choice = st.radio(
                "Radio button fill-null options",
                option_labels,
                index=default_index,
                key=radio_key,
                label_visibility="collapsed",
            )
            column_choices[field_name] = user_choice
            
            # Track radio interaction (only for enum columns where we need to reset dropdown)
            if is_enum_required_column:
                last_interaction_key = f"last_interaction_{selected_table_name}_{field_name}_{field_index}"
                prev_radio_key = f"prev_radio_{selected_table_name}_{field_name}_{field_index}"
                prev_radio_value = st.session_state.get(prev_radio_key, None)
                
                # Check if radio value actually changed
                if prev_radio_value != user_choice:
                    # Radio was just changed - mark it as last interaction
                    st.session_state[last_interaction_key] = "radio"
                    st.session_state[prev_radio_key] = user_choice

        # Column for per-column free-text comments.
        with comments_column:
            column_comments = st.session_state.get("column_comments", {})
            if selected_table_name not in column_comments:
                column_comments[selected_table_name] = {}
            table_comments = column_comments[selected_table_name]

            existing_comment_text = table_comments.get(field_name, "")

            comment_widget_key = (
                f"mv_comment_{section_kind}_{selected_table_name}_{field_name}_{field_index}"
            )

            if comment_widget_key not in st.session_state:
                st.session_state[comment_widget_key] = existing_comment_text

            ### Free-text Add comment box
            st.markdown(free_text_markdown, unsafe_allow_html=True)
            comment_value = st.text_area(
                "Free text comment box",
                key=comment_widget_key,
                height=15,
                label_visibility="collapsed",
            )

            table_comments[field_name] = comment_value
            column_comments[selected_table_name] = table_comments
            st.session_state["column_comments"] = column_comments
    return columns_with_missing
