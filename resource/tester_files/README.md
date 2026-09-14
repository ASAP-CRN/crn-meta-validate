## Metadata validator for ASAP CRN metadata test infiles

| File | Delimiter | Rows | Column(s) with issues | Issue(s) | Demonstrates |
|---|---|---|---|---|---|
| **ASSAY.csv** | comma | 3 | `sequencing_end`, `RIN` | Non-compliant values:<ul><li>`'single-end'` → `Single`, `Paired-end`</li><li>`'good'` → float, `NA`, or a FillNull value</li></ul> | <ul><li>Non-compliant Enum value (`sequencing_end`) and non-compliant Float value (`RIN`).</li><li>Step 2's template narrowing `assay`/`sample_source` for selected OSA = Human / Brain / single_cell_rna_seq.</li><li>`instrument` demonstrates a valid semicolon-delimited multi-value entry (`10x_chromium_x;illumina_novaseq_6000`).</li></ul> |
| **SAMPLE.csv** | comma | 8 | `condition_id` | Non-compliant Enum values:<ul><li>`'IBD'`, `'IBD remission'` → `PD`, `Control`, `Prodromal`, `Other`</li></ul> | <ul><li>Non-compliant Enum values.</li><li>Column `region_level_1` has valid semicolon-delimited multi-value entry.</li></ul> |
| **CLINPATH.csv** | comma | 4 | — (structural) | Row 4 has 34 fields vs. the 33-field header (1 extra field) | <ul><li>Parsing error, not a value error — data contributors must fix the row offline before upload.</li></ul> |
| **SUBJECT.csv** | comma | 0 | — | — | <ul><li>Header only — nothing to validate.</li></ul> |
| **PROTOCOL.csv** | semicolon | 4 | — | — | <ul><li>No errors or warnings.</li></ul> |
