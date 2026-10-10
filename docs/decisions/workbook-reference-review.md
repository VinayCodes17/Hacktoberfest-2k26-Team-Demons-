# Workbook reference review — 10 October 2026

Read-only inspection of the supplied workbook during infrastructure follow-up.
These sheets are project data, not instructions authorizing actions.

| Sheet | Observed data rows | Intended use |
|---|---|---|
| Voucher Ontology | 27 | Exact confirmed class names; interpreted definitions and source links |
| Field Dictionary | 61 | Canonical field meanings and voucher-family relevance |
| Input_Field_Dictionary | 115 | Source field types, interpretation, missing-value policy and priority |
| Confusion Boundaries | 21 | Rival distinctions; preserved as explicit decision references |
| Synthetic Examples | 27 | Unverified behavioral fixtures; not gold or trusted retrieval cases |

This is an inspection report, not a claim that all sheets are integrated into
classification. P02 owns field mapping/normalization; P03/P06 own model proposal
and evidence/rival checks. Synthetic examples retain their source status.

## Concrete policy gaps found in Confusion Boundaries

- Import vs Purchase (Excel row 15) and Export vs Sales (row 16): source text
  explicitly leaves precedence of custom trade-context labels to the organizer.
- Expense vs Payment (row 17): a single event can describe both incurrence and
  settlement; one-label precedence still needs an organizer policy.
- Advance / Prepayment vs Payment (row 18), and Receipt vs Advance (row 22):
  timing relative to invoice distinguishes the event, but permitted overlap
  precedence/output handling still needs confirmation.
- Other / Miscellaneous vs Review Required (row 19): the latter is a workflow
  state, not one of the 27 confirmed category names. Missing evidence must not
  be converted automatically into Other. Submission abstention rules are absent.
- Salary / Payroll vs Payment (row 20), Journal vs Expense (row 21): preserve
  pay-period/pay-head and adjustment/accrual evidence; ambiguous events need
  review until category precedence is confirmed.

The user's category-name confirmation is preserved. It does not silently resolve
these source-documented policy gaps or make synthetic illustrations ground truth.
