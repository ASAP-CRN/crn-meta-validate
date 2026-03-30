# Frequently Asked Questions

## General

??? question "What is the CDE?"
    CDE stands for **Common Data Elements** — the ASAP CRN controlled vocabularies that define valid values for specific metadata columns. The current version is hosted as a [Google Sheet](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).

??? question "What is an Enum column?"
    An `Enum` (enumeration) column only accepts values from a predefined list. The valid values are listed in row 5 of the template CSV and enforced during Step 5 validation.

## Files and uploads

??? question "Do I need to validate all my tables before uploading?"
    Yes — run Steps 1–5 for each CSV file separately. The app handles one table at a time.

??? question "Why can't I click the sanitized CSV download button?"
    The `.cde_compared.csv` download is disabled if your table has any ❌ errors. Fix all errors and re-run the CDE comparison — the button will enable once validation passes cleanly.

??? question "My file uses semicolons / tabs instead of commas. What do I do?"
    The app will detect this in Step 4 and guide you through fixing the delimiter. Alternatively, re-save your file as a proper comma-separated CSV before uploading.

??? question "Excel is reformatting my date values — what should I do?"
    This is a known Excel issue with date-like strings (e.g. `2023-01-01`). We recommend filling out your templates using a script (Python, R) or Google Sheets to avoid this. If this is not possible at this time, add a `'` to the start of the value, like `'May1`, this would keep the value as `May1` not transform it to a date.

## Validation results

??? question "What's the difference between an error and a warning?"
    **Errors (❌)** must be fixed — the sanitized CSV download will be blocked until they are resolved.     
    **Warnings (⚠️)** are recommended fixes but you can proceed without them if you have a valid reason (use the comment box to explain).

??? question "A column value is flagged as invalid but I believe it's correct. What do I do?"
    Use the free-text comment box next to that column to explain your reasoning to ASAP curators. Then download the `TABLE_comments.md` file and include it with your submission.

## Getting help

??? question "Who do I contact if I have questions?"
    Email [support@dnastack.com](mailto:support@dnastack.com) or open a [GitHub issue](https://github.com/ASAP-CRN/crn-meta-validate/issues/new/choose). Include a screenshot of the error and, if possible, the log `.md` file downloaded from the app.
