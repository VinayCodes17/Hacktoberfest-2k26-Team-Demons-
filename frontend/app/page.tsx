import { ArrowDownToLine, ArrowRight, BookOpen, Check, CircleDot, Database, FileSpreadsheet, Layers3, RefreshCw, ShieldCheck } from "lucide-react";
import { getReadiness } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const readiness = await getReadiness();
  const serviceReady = readiness?.service_ready === true;
  const readyCount = readiness?.checks.filter(check => check.status === "ready").length ?? 0;

  return (
    <div className="workspace">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="HisabhParakh home"><span className="brand-mark">ह</span><span>Hisabh<span className="brand-light">Parakh</span><small>TEAM DEMONS</small></span></a>
        <div className="workspace-label">LOCAL WORKSPACE <span>01</span></div>
        <nav aria-label="Workspace"><a href="#overview" className="nav-active"><Layers3 size={18} /> Overview <span>↗</span></a><a href="#readiness"><ShieldCheck size={18} /> Service readiness</a><a href="#workflow"><BookOpen size={18} /> Workflow</a></nav>
        <div className="sidebar-note"><span className="local-dot" /> Built to run locally<p>Your workbook stays in your local workflow.</p></div>
        <div className="sidebar-footer"><span className="avatar">TD</span><div>Team Demons<small>Development workspace</small></div></div>
      </aside>
      <div className="main-shell">
        <header className="topbar"><span>Workspace <span className="slash">/</span> <strong>Overview</strong></span><span className="environment"><CircleDot size={13} /> Local development</span></header>
        <main id="overview">
          <div className="page-heading"><div><p className="eyebrow">YOUR VOUCHER WORKSPACE</p><h1>A clear view. A checked decision.</h1><p className="intro">Classify with context, trace the evidence, and review what needs a closer look.</p></div><span className="phase-badge">Foundation · P01</span></div>
          <section className="welcome-card" aria-labelledby="welcome-title"><div className="welcome-copy"><span className="small-label">GETTING STARTED</span><h2 id="welcome-title">The foundation is taking shape.</h2><p>Check your local services below. Workbook upload and classification will become available as the next stages are connected.</p><a href="#readiness" className="primary-button">Check workspace readiness <ArrowRight size={16} /></a></div><div className="document-art" aria-hidden="true"><div className="art-back" /><div className="art-front"><FileSpreadsheet size={29} strokeWidth={1.3} /><span className="art-line wide" /><span className="art-line" /><div className="art-grid">{Array.from({ length: 12 }, (_, i) => <span key={i} />)}</div><span className="art-check"><Check size={20} /></span></div><span className="art-caption">SOURCE → EVIDENCE → REVIEW</span></div></section>
          <section className="summary-strip" aria-label="Workspace state"><div><span className="summary-icon"><Database size={19} /></span><div><small>API service</small><strong>{serviceReady ? "Available" : readiness ? "Needs attention" : "Not connected"}</strong></div></div><div><span className="summary-icon"><ShieldCheck size={19} /></span><div><small>Service checks</small><strong>{readiness ? `${readyCount} of ${readiness.checks.length} ready` : "Awaiting connection"}</strong></div></div><div><span className="summary-icon"><FileSpreadsheet size={19} /></span><div><small>Classification</small><strong>{readiness?.classification_ready ? "Available" : "Not ready yet"}</strong></div></div></section>
          <section className="readiness-section" id="readiness"><div className="section-heading"><div><p className="eyebrow">BEFORE YOU BEGIN</p><h2>Service readiness</h2></div><a href="/" className="refresh-button"><RefreshCw size={14} /> Refresh checks</a></div><p className="section-description">Current checks from your local API. A running service does not mean classification is ready.</p>
            {!readiness ? <div className="offline-state" role="status"><Database size={26} /><h3>The local API isn’t connected.</h3><p>Start the backend service, then refresh these checks. No live status is available yet.</p></div> : <div className="checks-list">{readiness.checks.map((check, index) => <div className="check-row" key={check.name}><span className="check-number">{String(index + 1).padStart(2, "0")}</span><div className="check-copy"><h3>{check.name}</h3><p>{check.message}</p></div><span className={`status-pill ${check.status}`}><span />{check.status === "ready" ? "Ready" : check.status === "optional" ? "Optional" : check.status === "unavailable" ? "Unavailable" : "Pending"}</span></div>)}</div>}
          </section>
          <section className="workflow-section" id="workflow"><div className="section-heading"><div><p className="eyebrow">WHAT COMES NEXT</p><h2>From workbook to a reviewed result</h2></div><span className="muted-label">Upcoming workflow</span></div><div className="workflow-grid"><article><span className="workflow-icon"><FileSpreadsheet size={22} /></span><span className="step-label">STEP 01</span><h3>Bring your workbook</h3><p>Inspect sheets and confirm which columns describe each transaction.</p></article><article><span className="workflow-icon"><BookOpen size={22} /></span><span className="step-label">STEP 02</span><h3>Follow the evidence</h3><p>Compare category definitions and inspect the source behind a recommendation.</p></article><article><span className="workflow-icon"><ArrowDownToLine size={22} /></span><span className="step-label">STEP 03</span><h3>Review, then export</h3><p>Resolve uncertain decisions and keep every source transaction accounted for.</p></article></div></section>
          <footer className="page-footer"><span>HisabhParakh <span className="footer-dot">·</span> Evidence before acceptance.</span><span>Local prototype · No classification results yet</span></footer>
        </main>
      </div>
    </div>
  );
}
