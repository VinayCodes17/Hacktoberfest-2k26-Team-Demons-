## 8. Security, reliability and performance acceptance matrix

| Scenario | Expected observable outcome | Owning phase |
|---|---|---|
| Missing taxonomy / ambiguous mapping | Classification blocked with actionable reason | P0/P2/P3 |
| Blank versus zero versus false | Preserved distinctions, correct provenance | P2 |
| Multi-sheet duplicate invoices | Every scoped transaction accounted for | P2/P4 |
| Spreadsheet instructions or formula-like output | Treated as data; generated text cells inert | P2/P4/P6 |
| Empty memory | Explicit ontology-only mode | P3/P5 |
| Memory outage | Visible error or explicitly configured degradation | P5 |
| Test/near-duplicate retrieval attempt | Excluded despite matching label/similarity | P5/P7 |
| Invalid JSON / evidence / label | Bounded repair or review; never false acceptance | P3/P6 |
| Model timeout or process crash | Attempt budget retained; row resume without duplicate result | P3 |
| Reviewer conflict / unauthorized write | Rejected with audit; original result retained | P6 |
| Candidate edits evaluator or labels | Proposal rejected | P8 |
| Index built but activation crashes | Old complete bundle remains active | P9 |
| Rollback during running job | Running job pinned; subsequent job uses restored version | P9 |
| Full RAM/VRAM pressure | Bounded concurrency; recorded failure/offload tradeoff | P0/P10 |
| Strict export with unresolved rows | Review output available; submission blocker list | P4 |
| Network disabled after cache warm-up | Full local flow passes or limitation documented | P10 |

Start with one generative session, CPU embeddings and compact context. Trim redundant exemplars before truncating decisive evidence or official definitions. If all labels do not fit, fail/review with a context-budget reason or use a measured wider-runtime configuration; do not silently discard labels. Configuration values for file limits, context, row deadlines and tokens must be explicit and profiled, not represented as optimized before measurement.
