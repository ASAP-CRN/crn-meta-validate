## Metadata validator for ASAP CRN metadata test infiles

| File | Delimiter | Rows | Column(s) with issues | Issue(s) | Demonstrates |
|---|---|---|---|---|---|
| **ASSAY.csv** | comma | 3 | `sequencing_end`, `RIN`, `reference_genome_or_genome_collection` | <ul><li>`'dual'` → `Single`, `Paired-end`</li><li>`'good'` → float, `NA`, or a FillNull value</li><li>`reference_genome_or_genome_collection` is empty in every row → any FillNull value or a valid token</li></ul> | <ul><li>Non-compliant Enum and Float values.</li><li>Filling out `reference_genome_or_genome_collection` column with a valid Enum value.</li><li>Valid semicolon-delimited multi-value entry (`instrument` = `10x_chromium_x;illumina_novaseq_6000`).</li></ul> |
| **SAMPLE.csv** | comma | 8 | `condition_id`, `preservation_method` | <ul><li>`'IBD'`, `'IBD remission'` → `PD`, `Control`, `Prodromal`, `Other`</li><li>`preservation_method` is empty in every row → any FillNull value or a valid token</li></ul> | <ul><li>Non-compliant Enum value.</li><li>Filling out `preservation_method` column with a valid Enum value.</li><li>Valid semicolon-delimited multi-value entry (`region_level_1` = `SNC;SNR`).</li></ul> |
| **CLINPATH.csv** | comma | 4 | — (structural) | Row 4 has 31 fields vs. the 30-field header (1 extra field) | <ul><li>Parsing error, not a value error — data contributors must fix the row offline before upload.</li></ul> |
| **SUBJECT.csv** | comma | 0 | — | — | <ul><li>Header only — nothing to validate.</li></ul> |
| **PROTOCOL.csv** | semicolon | 1 | — | — | <ul><li>No errors or warnings.</li></ul> |
