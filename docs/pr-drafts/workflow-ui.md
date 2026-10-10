# Connect Excel upload, visible progress, and downloadable results

Users previously saw a plain form without upload feedback or a results download.
The browser also depended on a hardcoded API address. Use a same-origin proxy and
an animated four-step workflow: upload, inspect mapping, classify/verify, review
and download. Upload percentage is real; inspection remains indeterminate until
the backend responds; classification counts come from persisted row states.

Restore the current job after refresh, show reconnecting/errors, filter results,
and export every completed job row with explanations and original source cells.
Keep review/error rows and write formula-like text as inert XLSX strings. Exports
are development review workbooks, not official organizer submissions.

Validation: 117 backend tests, TypeScript, Docker production build, 5 passing
Chrome checks (duplicate mobile inference skipped). Full 500-row upload/mapping
passed on desktop/mobile; one-row live inference, refresh recovery and download
passed end to end. Download reopened with OpenPyXL. See workflow-ui.json evidence.
