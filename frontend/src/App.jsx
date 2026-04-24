import { useCallback, useEffect, useState } from "react";
import { ActivityFeed } from "./components/ActivityFeed.jsx";
import { AuditLog } from "./components/AuditLog.jsx";
import { DataTable } from "./components/DataTable.jsx";
import { FileUpload } from "./components/FileUpload.jsx";
import { IssuesSummary } from "./components/IssuesSummary.jsx";
import { useSSE } from "./hooks/useSSE.js";

export default function App() {
  const [stage, setStage] = useState("upload");
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ghostStats, setGhostStats] = useState(null);

  const updateBatch = useCallback((nextBatch) => {
    setBatch((current) => ({ ...(current || {}), ...nextBatch }));
  }, []);

  const { events, isConnected, error } = useSSE(batch?.batch_id, updateBatch);

  useEffect(() => {
    const ghostEvent = events.find((event) => ["ghost_persisted", "ghost_skipped", "ghost_failed"].includes(event.type));
    if (ghostEvent && !ghostStats) setGhostStats(ghostEvent);
  }, [events, ghostStats]);

  async function upload(file) {
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/cleanup/start", { method: "POST", body: form });
    const data = await response.json();
    setBatch(data);
    setStage("issues");
    setLoading(false);
  }

  async function launch() {
    setLoading(true);
    await fetch(`/api/cleanup/launch/${batch.batch_id}`, { method: "POST" });
    setStage("processing");
    setLoading(false);
  }

  async function verify(jobId) {
    await fetch(`/api/verify/${jobId}`, { method: "POST" });
    const response = await fetch(`/api/status/batch/${batch.batch_id}`);
    setBatch(await response.json());
  }

  const jobs = batch?.jobs || [];

  return (
    <main>
      <header className="topbar">
        <div>
          <span className="eyebrow">CRM Heal</span>
          <h1>Autonomous CRM Cleanup Mission Control</h1>
        </div>
        {batch && <a className="export" href={`/api/export/${batch.batch_id}`}>Export Clean CSV</a>}
      </header>

      {stage === "upload" && <FileUpload onFile={upload} isLoading={loading} />}
      {stage === "issues" && <IssuesSummary summary={batch.summary} onLaunch={launch} isLaunching={loading} />}
      {stage === "processing" && (
        <>
          <section className="mission-grid">
            <DataTable jobs={jobs} onVerify={verify} />
            <ActivityFeed events={events} connected={isConnected} error={error} />
          </section>
          <AuditLog events={events} ghostStats={ghostStats} />
        </>
      )}

      <footer>Built with Redis • TinyFish • Vapi • Guild.ai • Ghost</footer>
    </main>
  );
}
