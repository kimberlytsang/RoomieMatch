# Design changes (Sprint 3, Section 6)

Where the code departs from the Sprint 2 design: one line naming what changed and why.

| # | Change | Why |
|---|---|---|
| 1 | US-01 rejects passwords that are shorter than 8 characters, common, entirely numeric, longer than 128 characters, or missing an uppercase letter or symbol. | Sprint 2 specifies a weak-password error and asks for requirements to be shown on the form, but leaves the exact rules and error wording open; these rules were defined during implementation. |
