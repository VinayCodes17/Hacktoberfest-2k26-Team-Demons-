"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { UploadCloud, FileSpreadsheet, Check, ArrowRight, LoaderCircle, Download, AlertCircle, Search, Rows3, ShieldCheck, RotateCcw, XCircle, FilePlus2 } from "lucide-react";

type Stage = "idle" | "uploading" | "inspecting" | "mapping" | "starting" | "classifying" | "complete";
type Report = {dataset_id: string; mapping_id: string; harness_id: string; selected_sheet: string;
  total_rows: number; warnings: string[]; mapping: {canonical_to_column: Record<string,string>; first_data_row: number; last_data_row: number}};
type Result = {id: string; transaction_id: string; payload: {status: string; proposed_label: string | null; rationale_summary?: string; reason_codes?: string[]; evidence_paths?: string[]; missing_evidence?: string[]; top_alternative?: string | null}};
type Progress = {total: number; queued: number; running: number; completed: number; failed: number; active_row?: {physical_row: number; sheet: string} | null};
const API = "/api/backend";
const SAVED_JOB = "hisabhparakh-active-job";
const steps = [
  {title: "Upload workbook", detail: "Your Excel stays local", icon: UploadCloud},
  {title: "Check mapping", detail: "Confirm sheets & fields", icon: Search},
  {title: "Classify & verify", detail: "Follow each saved result", icon: ShieldCheck},
  {title: "Review & download", detail: "Every row accounted for", icon: Download},
];
function message(error: unknown) { return error instanceof Error ? error.message : "Something went wrong. Please retry."; }
async function read(response: Response) {
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.message || "The service did not respond. Please retry.");
  if (!data) throw new Error("The service returned an unreadable response. Please retry.");
  return data;
}
export default function WorkflowApp() {
  const reduced = useReducedMotion();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sheet, setSheet] = useState("");
  const [filename, setFilename] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [upload, setUpload] = useState(0);
  const [drag, setDrag] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [downloading, setDownloading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const busy = ["uploading", "inspecting", "starting", "classifying"].includes(stage);
  const activeStep = ["idle", "uploading"].includes(stage) ? 0 : ["inspecting", "mapping"].includes(stage) ? 1 : stage === "complete" ? 3 : 2;
  const finished = progress ? progress.completed + progress.failed : 0;
  const percent = progress?.total ? Math.round(finished / progress.total * 100) : 0;
  const counts = {accepted: results.filter(r => r.payload.status === "accepted").length,
    review: results.filter(r => r.payload.status === "review").length,
    error: results.filter(r => r.payload.status === "error").length};
  const visible = results.filter(r => filter === "all" || r.payload.status === filter);
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(SAVED_JOB) || "null");
      if (saved && typeof saved.id === "string" && /^[a-zA-Z0-9-]+$/.test(saved.id)) {
        setJob(saved.id); setFilename(typeof saved.filename === "string" ? saved.filename : "Saved workbook"); setStage("classifying");
      }
    } catch { /* Storage is optional; the job remains persisted on the backend. */ }
  }, []);
  useEffect(() => {
    if (!job) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const [next, predictions] = await Promise.all([
          fetch(`${API}/jobs/${job}/progress`, {signal: controller.signal}).then(read),
          fetch(`${API}/jobs/${job}/predictions`, {signal: controller.signal}).then(read),
        ]);
        if (stopped) return;
        setError(""); setProgress(next); setResults(predictions);
        // Separate requests can race; do not show completion until every result is visible.
        if (next.total > 0 && next.completed + next.failed === next.total && predictions.length === next.total) setStage("complete");
        else timer = setTimeout(poll, 2000);
      } catch (e) {
        if (!stopped) { setError(`${message(e)} Reconnecting automatically; the job continues in the background.`); timer = setTimeout(poll, 5000); }
      }
    }
    poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [job]);
  function choose(next: File | undefined) {
    if (!next || busy) return;
    setError("");
    if (!next.name.toLowerCase().endsWith(".xlsx")) { setError("Choose an .xlsx Excel workbook."); return; }
    if (next.size > 50 * 1024 * 1024) { setError("This workbook is larger than 50 MiB. Choose a smaller file."); return; }
    setFile(next); setFilename(next.name); setReport(null); setStage("idle"); setProgress(null); setResults([]); setJob(null);
    try { localStorage.removeItem(SAVED_JOB); } catch {}
  }
  async function inspect() {
    if (!file) return;
    setError(""); setStage("uploading"); setUpload(0);
    const data = new FormData(); data.append("file", file);
    if (sheet.trim()) data.append("sheet_name", sheet.trim());
    try {
      const response = await new Promise<Report>((resolve, reject) => {
        const xhr = new XMLHttpRequest(); xhr.open("POST", `${API}/datasets/profile`); xhr.timeout = 120000;
        xhr.upload.onprogress = e => { if (e.lengthComputable) setUpload(Math.round(e.loaded / e.total * 100)); };
        xhr.upload.onload = () => { setUpload(100); setStage("inspecting"); };
        xhr.onerror = () => reject(new Error("Upload could not reach the local service. Check your connection and retry."));
        xhr.ontimeout = () => reject(new Error("Workbook inspection timed out. Retry or select a smaller workbook."));
        xhr.onload = () => {
          try {
            const value = JSON.parse(xhr.responseText);
            if (xhr.status < 200 || xhr.status >= 300) {
              const detail = [...(value.report?.errors || []), ...(value.report?.mapping_errors || [])].join(" ");
              reject(new Error(`${value.message || "Workbook inspection failed."} ${detail}`));
            } else resolve(value);
          } catch { reject(new Error("The service returned an unreadable response. Please retry.")); }
        };
        xhr.send(data);
      });
      setReport(response); setStage("mapping");
    } catch (e) { setError(message(e)); setStage("idle"); }
  }
  async function classify() {
    if (!report) return;
    setError(""); setStage("starting");
    try {
      const result = await read(await fetch(`${API}/jobs`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
        dataset_id: report.dataset_id, mapping_id: report.mapping_id, harness_id: report.harness_id, idempotency_key: `ui-${report.dataset_id}`})}));
      try { localStorage.setItem(SAVED_JOB, JSON.stringify({id: result.id, filename})); } catch {}
      setJob(result.id); setStage("classifying");
    } catch (e) { setError(message(e)); setStage("mapping"); }
  }
  async function download() {
    setDownloading(true); setError("");
    try {
      const response = await fetch(`${API}/jobs/${job}/export.xlsx`);
      if (!response.ok) await read(response);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url; link.download = `${filename.replace(/\.xlsx$/i, "") || "workbook"}-classified.xlsx`;
      document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(message(e)); } finally { setDownloading(false); }
  }
  function reset() {
    setJob(null); setFile(null); setReport(null); setResults([]); setProgress(null); setError(""); setStage("idle"); setFilter("all"); setFilename(""); setCancelling(false);
    try { localStorage.removeItem(SAVED_JOB); } catch {}
  }
  async function cancelJob() {
    if (!job || cancelling) return;
    setCancelling(true); setError("");
    try {
      await read(await fetch(`${API}/jobs/${job}/cancel`, {method: "POST"}));
      setStage("complete");
    } catch (e) { setError(message(e)); } finally { setCancelling(false); }
  }
  return <section className="classifier" aria-labelledby="classify-title">
    <div className="classifier-heading"><div><p className="eyebrow">WORKBOOK TO DECISION</p><h2 id="classify-title">Classify a workbook</h2><p>Bring your Excel. Follow the evidence. Take your results with you.</p></div><span className="local-chip"><span /> Processed locally</span></div>
    <ol className="process-steps" aria-label="Classification steps">{steps.map((step,i) => {
      const Icon = step.icon; const done = i < activeStep || stage === "complete";
      return <li key={step.title} className={`${done ? "step-done" : ""} ${i === activeStep ? "step-active" : ""}`} aria-current={i === activeStep ? "step" : undefined}>
        <span className="step-symbol">{done ? <Check size={18}/> : <Icon size={18}/>}</span><div><strong>{step.title}</strong><small>{step.detail}</small></div>
      </li>;
    })}</ol>
    {error && <div className="workflow-error" role="alert"><AlertCircle size={18}/><span>{error}</span></div>}
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={activeStep} initial={reduced ? false : {opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} exit={reduced ? undefined : {opacity: 0, y: -6}} transition={{duration: .22}} className="process-body">
        {stage === "idle" && <>
          <input ref={input} className="file-control" type="file" accept=".xlsx" aria-label="Excel workbook" onChange={e => choose(e.target.files?.[0])}/>
          <button type="button" className={`dropzone ${drag ? "dragging" : ""} ${file ? "has-file" : ""}`} onClick={() => input.current?.click()}
            onDragOver={e => {e.preventDefault(); setDrag(true);}} onDragLeave={() => setDrag(false)} onDrop={e => {e.preventDefault(); setDrag(false); choose(e.dataTransfer.files[0]);}}>
            <span className="upload-emblem">{file ? <FileSpreadsheet size={30}/> : <UploadCloud size={30}/>}</span>
            <strong>{file ? file.name : "Drop your Excel workbook here"}</strong>
            <span>{file ? `${(file.size / 1024).toFixed(0)} KB / Click to change file` : "or click to browse files"}</span><small>.xlsx files / up to 50 MiB</small>
          </button>
          <div className="upload-actions"><details className="sheet-options"><summary>Choose a specific sheet</summary><label>Sheet name<input value={sheet} onChange={e => setSheet(e.target.value)} placeholder="Leave blank to auto-detect"/></label></details>
            <button className="primary-button" disabled={!file} onClick={inspect}>Inspect workbook <ArrowRight size={16}/></button></div>
          <p className="workflow-note"><ShieldCheck size={14}/> Source cells stay unchanged. Answer columns are excluded from classification.</p>
        </>}
        {["uploading", "inspecting"].includes(stage) && <div className="processing-panel" role="status">
          <span className="processing-orbit"><FileSpreadsheet size={30}/><LoaderCircle className="spin" size={64}/></span>
          <h3>{stage === "uploading" ? "Uploading your workbook" : "Reading your workbook"}</h3><p>{filename}</p>
          <div className={`progress-track ${stage === "inspecting" ? "indeterminate" : ""}`}><span style={{width: stage === "inspecting" ? "35%" : `${upload}%`}}/></div>
          <small>{stage === "uploading" ? `${upload}% uploaded` : "Checking sheets, matching columns and preserving source evidence..."}</small>
        </div>}
        {stage === "mapping" && report && <>
          <div className="mapping-ready"><span className="success-icon"><Check size={22}/></span><div><h3>Workbook inspected</h3><p>{filename}</p></div><span className="local-chip">Ready for your check</span></div>
          <div className="mapping-stats"><div><small>Selected sheet</small><strong>{report.selected_sheet}</strong></div><div><small>Transactions found</small><strong>{report.total_rows.toLocaleString()}</strong></div><div><small>Fields mapped</small><strong>{Object.keys(report.mapping.canonical_to_column).length}</strong></div></div>
          <details className="mapping-details"><summary>Inspect column mapping <span>{Object.keys(report.mapping.canonical_to_column).length} fields</span></summary><div className="mapping-table"><table><thead><tr><th>Excel column</th><th>Transaction field</th></tr></thead><tbody>{Object.entries(report.mapping.canonical_to_column).map(([key,value]) => <tr key={key}><td>{value}</td><td>{key}</td></tr>)}</tbody></table></div></details>
          <p className="workflow-note">Rows {report.mapping.first_data_row} to {report.mapping.last_data_row}; blank rows excluded. Each physical row is one transaction.</p>
          {report.warnings.length > 0 && <details className="mapping-details"><summary>Inspection notes ({report.warnings.length})</summary>{report.warnings.map((w,i) => <p key={i}>{w}</p>)}</details>}
          <div className="upload-actions"><button className="text-button" onClick={() => setStage("idle")}>Change file or sheet</button><button className="primary-button" onClick={classify}>Confirm mapping and classify <ArrowRight size={16}/></button></div>
        </>}
        {["starting", "classifying", "complete"].includes(stage) && <>
          <div className="run-heading"><span className={stage === "complete" ? "success-icon" : "processing-icon"}>{stage === "complete" ? <Check size={22}/> : <LoaderCircle className="spin" size={22}/>}</span><div><h3>{stage === "complete" ? "Your results are ready" : stage === "starting" ? "Starting classification" : "Classifying and checking evidence"}</h3><p>{filename || "Your workbook"}</p></div><strong className="percent-count">{percent}%</strong></div>
          <div className="progress-track" role="progressbar" aria-label="Transactions processed" aria-valuenow={finished} aria-valuemin={0} aria-valuemax={progress?.total || report?.total_rows || 1}><span style={{width: `${percent}%`}}/></div>
          <div className="progress-caption" aria-live="polite"><span>{finished} of {progress?.total || report?.total_rows || "..."} rows processed</span><span>{stage === "complete" ? "All rows saved" : progress?.active_row ? `Working on Excel row ${progress.active_row.physical_row}` : "Waiting for the local worker"}</span></div>
          {stage !== "complete" && <div className="classify-actions"><p className="workflow-note">Local inference can take a little time. Results appear as rows finish. Refreshing this page resumes your saved job.</p><div className="cancel-row"><button className="danger-button" disabled={cancelling} onClick={cancelJob}>{cancelling ? <><LoaderCircle className="spin" size={15}/> Cancelling…</> : <><XCircle size={15}/> Cancel process</>}</button><button className="text-button" onClick={reset}><FilePlus2 size={14}/> New file</button></div></div>}
          <div className="result-counts"><div><ShieldCheck size={19}/><strong>{counts.accepted}</strong><span>Passed checks</span></div><div><Search size={19}/><strong>{counts.review}</strong><span>Needs review</span></div><div><AlertCircle size={19}/><strong>{counts.error}</strong><span>Errors</span></div></div>
          {stage === "complete" && <div className="result-actions"><p>{counts.review || counts.error ? "Some rows need your attention. They are included in the download." : "Inspect the proposals before using them in your accounts."}<small>Includes classifications, explanations and source evidence.</small></p><button className="primary-button" disabled={downloading} onClick={download}>{downloading ? <LoaderCircle className="spin" size={17}/> : <Download size={17}/>} {downloading ? "Preparing download" : "Download Excel results"}</button></div>}
          {results.length > 0 && <><div className="result-filters" aria-label="Filter results">{["all", "accepted", "review", "error"].map(value => <button key={value} aria-pressed={filter === value} className={filter === value ? "selected" : ""} onClick={() => setFilter(value)}>{({all: "All results", accepted: "Passed checks", review: "Needs review", error: "Errors"})[value]}</button>)}</div>
            <div className="results-list">{visible.length === 0 ? <p className="empty-results">No rows in this group.</p> : visible.map(result => <details key={result.id} className="result-row"><summary><span className="source-row"><Rows3 size={15}/> Row {result.transaction_id.split(":").pop()}</span><strong>{result.payload.proposed_label || "No proposal"}</strong><span className={`decision-badge ${result.payload.status}`}>{result.payload.status === "accepted" ? "Passed checks" : result.payload.status === "review" ? "Needs review" : "Error"}</span></summary><div className="result-explanation"><p>{result.payload.rationale_summary || "No valid proposal was saved. See the reason below."}</p><dl><dt>Alternative</dt><dd>{result.payload.top_alternative || "None proposed"}</dd><dt>Evidence fields</dt><dd>{result.payload.evidence_paths?.join(", ") || "None"}</dd><dt>Review reasons</dt><dd>{result.payload.reason_codes?.join(", ") || "None"}</dd></dl></div></details>)}</div></>}
          {stage === "complete" && <div className="workflow-bottom"><span>Development review output. Not an approved organizer submission.</span><button className="text-button" onClick={reset}><RotateCcw size={14}/> Process another workbook</button></div>}
        </>}
      </motion.div>
    </AnimatePresence>
  </section>;
}
