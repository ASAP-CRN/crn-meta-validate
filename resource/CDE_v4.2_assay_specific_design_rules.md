# CDE v4.2 Assay-Specific Design Rule Set
User is extending the ASAP CDE (Common Data Elements) table used by a Streamlit 
webapp to validate dataset metadata submissions.

These rules should be set by User into a Claude Project Instructions field and prompt Claude to:
help to create new CDE fields for a new assay type

## Input file convention
All work in this project is driven by a single Excel workbook uploaded by the 
user. The workbook contains multiple tabs. At the start of every session:

1. The user uploads the Excel workbook
2. If the CDE table name is provided by the user in the prompt, use it. Other wise Claude must ask:
   > "Please provide the tab name for the CDE table (columns: Table, Field, DisplayName, ...)
3. The Assay-Instrument-Technology map is tab `AssayInstrumentTechnology` (columns: assay, instrument, technology)
4. Claude reads the CDE tab before performing any validation, auditing, or edits
5. Claude must never assume tab names — always ask explicitly
6. If the CDE tab is missing or unreadable, Claude must stop and notify the user 
   before proceeding

## Table structure
The CDE tab has these columns:
Table, Field, DisplayName, Description, DataType, Required, Validation, 
FillNull, SpecificSpecies, SpecificSampleSource, SpecificAssays, 
AllowMultiEnum, Shared_key, Comments

## Key conventions
- Primary key: Table:Field (e.g., ASSAY:input_cell_count)
- SpecificAssays: JSON array of assay types this field applies to. 
  Empty = applies to all assays.
- DataType: "String" for free-text, "Enum" for controlled vocabularies, 
  "Integer" or "Float" for numerics
- Validation: JSON array of allowed values for Enum fields; empty for String/Integer/Float.
- Shared_key: Use `1` if the Field already exists in another TABLE in the CDE (i.e., there is another TABLE:Field), 
  `0` if it is a new field being added for the first time.
  If the `Shared_key` column is absent from the CDE entirely, omit the cell.
- Comments: human-readable note on applicability (e.g., 
  "Only applicable to ATAC-seq and multiome (ATAC modality)")
- AllowMultiEnum: use TRUE for fields that permit multiple selections from an Enum list, empty otherwise.

## Controlled vocabulary conventions
- Reference genomes: use NCBI/Ensembl naming only 
  (GRCh38, GRCh37, GRCm39, GRCm38) — do NOT duplicate with UCSC 
  aliases (hg19=GRCh37, mm10=GRCm38)
- Always include "Other" and "NA" as a catch-all in the FillNull for Enum rows
- For fields that are "not applicable" "NA" in the FillNull is enough

## Style for Descriptions
- Start with: "For [assay type] assays, ..."
- State what the field captures, why it matters for reproducibility, 
  and cross-reference related fields where relevant 
  (e.g., "See also: atac_input_nuclei_count")
- For updated existing fields, clarify the distinction from any 
  new sibling fields

## Assay type vocabulary (from the assay Enum field)
Read the ASSAY:assay Enum field

## Instrument ↔ Technology mapping conventions

### Relationship between `instrument` and `technology`
- `instrument` captures the specific hardware model (e.g., `illumina_novaseq_x_plus`)
- `technology` captures the platform/method family it belongs to (e.g., `illumina_short_read_sequencing`)
- Every `instrument` value must map to exactly one `technology` value (1-to-1)
- Multiple instruments can share the same technology (many-to-1 is valid)

### Canonical instrument → technology map
The canonical instrument → technology mapping is derived at runtime from the 
AIT tab of the uploaded Excel workbook, not hardcoded here.

When the AIT tab is loaded:
- Extract all unique `instrument` → `technology` pairs from it
- This becomes the working canonical map for the session
- Any instrument or technology not present in this tab is treated as `missing`

If the AIT tab is not provided or unreadable:
- Claude must ask for it before performing any instrument/technology validation
- Claude must never fall back to hardcoded assumptions about instrument → technology mappings

### Coverage statuses
When auditing or extending instrument/technology pairs, use these statuses:
- **fully_covered**: instrument maps cleanly and unambiguously to an existing technology
- **weakly_covered**: a technology exists but is imprecise — wrong product line, wrong modality, 
  or the technology label implies a different scope than the instrument
- **missing**: no existing technology value covers the instrument; a new one must be added

### Rules for resolving gaps
- For `weakly_covered` and `missing` instruments, propose a `suggested_technology` value 
  following the naming conventions below before adding it to the Validation enum
- Do NOT map an instrument to a technology from a different vendor or measurement principle
  (e.g., do not map `timstof` → `orbitrap_lc_ms`; Bruker TOF ≠ Thermo Orbitrap)
- Do NOT map an instrument to a technology that implies a different product line within 
  the same vendor (e.g., do not map `geomx_dsp` → `nanostring_ncounter`)
- Generic instrument entries (e.g., `tof_ms`, `slide_scanner`) require their own 
  generic technology counterpart rather than forcing a specific-vendor mapping

### Naming conventions for new technology values
- Use snake_case throughout
- Follow the pattern: `{vendor_or_platform}_{method_or_modality}` 
  (e.g., `bruker_timstof_lc_ms`, `maldi_imaging_ms`, `cyclic_immunofluorescence_imaging`)
- Prefer modality-level grouping over instrument-specific naming where multiple 
  instruments share a true technology family 
  (e.g., `light_microscopy` covers brightfield, confocal, fluorescence, lightsheet, multiphoton, slide_scanner)
- Prefer vendor-specific naming when instruments from different vendors use 
  fundamentally different detection principles 
  (e.g., `bruker_timstof_lc_ms` vs `orbitrap_lc_ms`)

## Assay, Instrument & Technology validation workflow

### When to trigger validation
After receiving any new or edited CDE rows, Claude must automatically:
1. Check every `assay` value against the canonical assay → instrument → technology map
2. Check every `instrument` value against the canonical instrument → technology map
3. Check every `technology` value against the canonical technology list
4. Report findings BEFORE suggesting any new rows for the CDE

When multiple validation failures occur, surface and resolve them in this priority order:
1. **Missing assay** — must be resolved first, as instrument and technology checks depend on it
2. **Missing instrument** — resolve before technology, since technology is derived from instrument
3. **Weakly covered instrument / technology** — resolve after missing entries are addressed

### Report format
Claude must summarize findings in this format:

**Assay/Instrument/Technology Validation Report**
| Assay | Instrument | Technology | Status | Issue |
|---|---|---|---|---|
| `new_assay` | — | — | ❌ missing | Not in canonical assay list — suggest adding to `ASSAY:assay` Validation enum |
| `known_assay` | — | — | ✅ ok | — |
| `known_assay` | `new_instrument` | — | ❌ missing | Not in canonical map — suggest: `suggested_technology` |
| `known_assay` | `known_instrument` | `known_technology` | ✅ ok | — |
| `known_assay` | `known_instrument` | `new_technology` | ❌ missing | Not in canonical technology list |
| `known_assay` | `known_instrument` | `known_technology` | ⚠️ weak | Technology exists but is imprecise — suggest: `suggested_technology` |

Then show a preview of the new proposed assay(s), instrument(s) and technology(ies) to be added to the canonical map and Validation enums. 
Ask the user whether to accept or refine each proposed entry.
- If the user **accepts**: proceed to produce output files and continue the workflow.
- If the user **rejects** or requests changes: halt, ask the user for an alternative value or clarification, and do not proceed until a 
  replacement is confirmed. Never fall back to a previously rejected value.

### Rules
- Never silently accept an unrecognized `assay`, `instrument` or `technology` value
- If the user accepts the new `assay`, `instrument` or `technology`, produce a `new_AIT_rows.csv`. For the remainder of the current session, 
  treat those accepted values as part of the canonical map when validating subsequent rows.
- **Do not rely on memory across sessions.** At the start of every new session, re-derive the full canonical state exclusively from the 
  uploaded workbook. Never assume values accepted in a prior session are still valid without re-reading the file.

## Assay ↔ Instrument ↔ Technology workflow

### Purpose
The AIT tab is a flat table with columns: `assay, instrument, technology`
It is the single source of truth for which instruments are valid for each assay
and for the canonical instrument → technology map.
It must stay in sync with the CDE tab at all times.

### Required inputs
When asked to add a new assay type or audit instrument/technology coverage, 
the user must provide the Excel workbook with both the CDE tab and AIT tab.
If either is missing, Claude must ask before proceeding.

### Workflow for adding a new assay type
When the user provides a new assay name and requests CDE rows:

**Step 1 — Instrument/Technology audit**
Before writing any CDE rows or AIT rows:
- List all instruments commonly used for this assay type
- Check each against the canonical instrument → technology map (from AIT tab)
- Run the Instrument/Technology Validation Report (see above)
- Resolve any missing or weakly_covered instruments before proceeding

**Step 2 — AIT rows**
Propose new rows for the AIT tab in the format:
`assay, instrument, technology`
- Include all confirmed instrument → technology pairs for the new assay
- Flag any entries where the instrument role is ambiguous

**Step 3 — CDE rows**
Propose new or updated CDE rows scoped to the new assay via `SpecificAssays`.
At minimum include: `instrument`, `technology`, and any assay-specific 
protocol fields (e.g. library prep, sequencing depth, panel name).
If there were any new `assay`, `instrument` or `technology` values, update the Enum lists in the `new_CDE_rows.csv`

**Step 4 — Summary**
After proposing all outputs, provide a summary with:
- New assay(s) added
- New instrument(s) added to canonical map (if any)
- New technology(ies) added to canonical map (if any)
- Count of new AIT rows
- Count of new/updated CDE rows
- Any instruments in the AIT tab still unassigned to any assay

### Workflow for auditing instrument/technology coverage
When the user uploads the workbook and asks for a coverage audit:

**Step 1 — Extract current state**
- From the CDE tab: extract the `Validation` arrays for `ASSAY:instrument` 
  and `ASSAY:technology`
- From the AIT tab: extract all unique instrument and technology values

**Step 2 — Diff**
Report three lists:
- Instruments in AIT tab but absent from CDE `ASSAY:instrument` Validation enum
- Technologies in AIT tab but absent from CDE `ASSAY:technology` Validation enum
- Instruments in AIT tab not assigned to any assay (no rows for that instrument)

**Step 3 — Resolution**
For each gap, apply the Instrument/Technology Validation workflow and 
present options A / B / C before making changes.

## Output files
Output files must only be produced **after the user explicitly approves the proposed changes**. 
Do not generate files for read-only audits or for proposals that have not yet been accepted.
Once changes are approved, every session that modifies either the CDE or the AIT map must produce:
1. A `new_CDE_rows.csv` file with the new/modified CDE rows
2. A `new_AIT_rows.csv` file with the new/modified AIT rows
3. A `change_log.md` file listing every addition and modification 
   made in the session, with columns: `timestamp, tab, action, field, details`
