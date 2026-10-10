## 6. Self-healing: exact behavioral specification

The practical distinction is between **operational recovery** and **supervised policy repair**. Online JSON repair/retry consumes the two-call budget and never learns a label. Offline policy repair needs trusted labels and a regression experiment.

```text
For each job:
  pin mapping + complete harness bundle
  for each transaction:
    normalize, route, retrieve eligible context
    reserve and persist attempt 1; classify
    validate schema, membership, source support and rival criteria
    if recoverable AND attempt budget remains AND deadline permits:
      reserve and persist attempt 2
      repair output OR reconsider pair; return complete revised proposal
      validate again without another generative call
    persist accepted/review/error plus every reason and trace

For an offline repair experiment:
  require trusted development labels and locked evaluation manifest
  mine repeated semantic errors; create bounded patch candidate
  validate allowed patch paths; freeze candidate bundle
  evaluate parent and candidate with fixed gates and eligible retrieval
  reject if any gate fails or required evidence is absent
  otherwise mark eligible for authorized activation
  validate artifacts, compare parent, atomically activate pointer
  retain old bundle; new jobs use new version, old jobs remain pinned
```

**Payment/Contra demonstration:** only if both labels exist in the official taxonomy, use confirmed development mistakes concerning explicit account ownership. Clarify the boundary using observed ownership versus external settlement. Show real source cells, candidate diff and matched evaluation. Do not handcraft a guaranteed successful score. Missing ownership should remain a review case; repeated model guesses never establish ownership.

**Proposed gate schema, intentionally not runnable defaults:** `min_macro_f1_gain`, `max_critical_class_recall_drop`, `max_p95_latency`, `max_peak_ram`, `max_peak_vram`, `max_proposals`, and `minimum_label_support` must be resolved before promotion. Required structural rules are exact: no invalid accepted labels, no accepted unsupported evidence, no split leakage, no online row above two calls, complete row accounting. Passing fixtures does not imply perfect real-world classification.
