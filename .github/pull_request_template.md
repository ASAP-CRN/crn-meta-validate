## Description
<!-- What does this PR do? One or two sentences. -->

## Linked issue / ticket
<!-- ClickUp or GitHub issue. Remove whichever doesn't apply. -->
- [ClickUp](<url>)
- [GitHub issue](<url>)

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Schema / CDE update
- [ ] Documentation
- [ ] Refactor / internal

---

<!-- ============================================================
     CHECKLIST — feature branch → dev
     (remove this section when opening dev → main)
     ============================================================ -->
## Feature-branch checklist (→ dev)

- [ ] All CI checks pass (lint, smoke-test, schema, readme-sync)
- [ ] New or changed logic covered by a quick manual test using `resource/tester_files/`
- [ ] If `app_schema` was changed: helper rows in template CSVs still correct
- [ ] If `help_menus.py` intro changed: `python utils/generate_readme.py -v <version>` run and committed
- [ ] PR description explains *why*, not just *what*

---

<!-- ============================================================
     CHECKLIST — dev → main  (release gate)
     Remove the feature-branch section above and use this one.
     ============================================================ -->
<!--
## Release checklist (→ main)

- [ ] All release-gate CI checks pass
- [ ] Tested end-to-end on Streamlit locally (`streamlit run app.py`)
- [ ] Tester files in `resource/tester_files/` reflect latest schema
- [ ] README version header updated (`python utils/generate_readme.py -v <version>`)
- [ ] `app_schema` version matches the one referenced in `app.py`
- [ ] No leftover debug prints or test-only schema IDs (e.g. test spreadsheet ID swapped back to prod)
- [ ] `kebab_menu.get_help_url` in app_schema points to correct docs URL
-->

