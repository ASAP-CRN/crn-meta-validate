import streamlit as st
import ast
import html
from typing import Any, Callable, Dict, List, Tuple

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







def _parse_fillnull_values(fillnull_text: str) -> List[str]:
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
    free_text: Dict[str, str],
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

        # Build FillNull-driven options, with DataType fallbacks
        fillnull_values = _parse_fillnull_values(fillnull_text)

        option_labels: List[str] = []
        if fillnull_values:
            for fill_value in fillnull_values:
                option_labels.append(f'Fill out with "{fill_value}"')
        else:
            if section_kind == "required":
                if datatype_lower in ("integer", "float"):
                    option_labels = [
                        "Fill out with N/A",
                        "Fill out with 0",
                    ]
                elif "enum" in datatype_lower:
                    suggested_label = "Fill out with first allowed value from Validation"
                    option_labels = [
                        suggested_label,
                        'Fill out with "Unknown"',
                        'Fill out with "Other"',
                    ]
                else:
                    option_labels = [
                        "Fill out with Unknown",
                        "Fill out with NA",
                    ]
            else:
                # Optional: simple defaults when FillNull is missing
                option_labels = [
                    "Fill out with Unknown",
                    "Fill out with NA",
                ]

        existing_choice = column_choices.get(field_name, option_labels[0])
        try:
            default_index = option_labels.index(existing_choice)
        except ValueError:
            default_index = 0

        # Hover tooltip: use only Description
        hover_parts: List[str] = []
        if description_text:
            hover_parts.append(description_text)
        hover_text = " | ".join(hover_parts)
        hover_text_escaped = html.escape(hover_text, quote=True)

        # Card styling (required vs optional)
        block_class = "missing-block-required" if section_kind == "required" else "missing-block-optional"
        severity_icon = "⚠️"
        section_label = "Required" if section_kind == "required" else "Optional"

        st.markdown(
            f'''
            <div class="missing-block {block_class}">
                <div class="missing-block-title">
                    {severity_icon} <strong>{section_label}</strong> column
                    <span class="tooltip-wrapper">
                        <span class="missing-hover"><strong>{field_name}</strong></span>
                        <span class="tooltip-text">{hover_text_escaped}</span>
                    </span>
                    has {missing_count} empty values. Expect data type: {datatype_text}.
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        # Radio label differs slightly between required and optional
        if section_kind == "required":
            radio_label = "Choose how to fill this column:"
            radio_key_prefix = "mv_radio_required"
        else:
            radio_label = "Choose how to fill this optional column:"
            radio_key_prefix = "mv_radio_optional"

        # Unique key for this radio, using a global call id and field name
        radio_key = f"{radio_key_prefix}_{selected_table_name}_{field_name}_{field_index}"

        user_choice = st.radio(
            radio_label,
            option_labels,
            index=default_index,
            key=radio_key,
        )
        column_choices[field_name] = user_choice

        # Required vs optional layout for free text and enum
        if section_kind == "required":
            free_text_col, enum_dropdown_col = st.columns(2)

            with free_text_col:
                free_text_key = f"mv_free_required_{selected_table_name}_{field_name}_{field_index}"
                existing_free_text = free_text.get(field_name, "")
                free_text_value = st.text_input(
                    "Free text (optional; overrides choice):",
                    value=existing_free_text,
                    key=free_text_key,
                )
                free_text[field_name] = free_text_value

            with enum_dropdown_col:
                if enum_choice is None:
                    enum_choice = {}

                enum_key = f"mv_enum_required_{selected_table_name}_{field_name}_{field_index}"
                existing_enum_choice = enum_choice.get(field_name, "")

                if "enum" in datatype_lower and validation_text:
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
                        if existing_enum_choice and existing_enum_choice not in validation_values:
                            validation_values = [existing_enum_choice] + validation_values

                        selected_enum_value = st.selectbox(
                            "Controlled vocabularies (optional; overrides choice):",
                            validation_values,
                            index=validation_values.index(existing_enum_choice)
                            if existing_enum_choice in validation_values
                            else 0,
                            key=enum_key,
                        )
                        enum_choice[field_name] = selected_enum_value
                    else:
                        enum_choice[field_name] = existing_enum_choice
                else:
                    enum_choice[field_name] = existing_enum_choice
        else:
            # Optional section: full-width free text only
            free_text_key = f"mv_free_optional_{selected_table_name}_{field_name}_{field_index}"
            existing_free_text_opt = free_text.get(field_name, "")
            free_text_value_opt = st.text_input(
                "Free text (optional):",
                value=existing_free_text_opt,
                key=free_text_key,
            )
            free_text[field_name] = free_text_value_opt

    return columns_with_missing