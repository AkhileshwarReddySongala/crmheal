import { AlertTriangle, Database, Mail, Phone, ShieldCheck, UserRoundX } from "lucide-react";

const cards = [
  ["Total Records", "total_records", Database],
  ["Duplicate Pairs", "duplicates", UserRoundX],
  ["Missing Email", "missing_email", Mail],
  ["Missing Phone", "missing_phone", Phone],
  ["Missing Title", "missing_title", AlertTriangle],
  ["Stale Records", "stale_records", ShieldCheck]
];

export function IssuesSummary({ summary, onLaunch, isLaunching }) {
  return (
    <section className="stage-panel">
      <div className="summary-grid">
        {cards.map(([label, key, Icon]) => (
          <article className="stat-card" key={key}>
            <Icon size={20} />
            <strong>{summary?.[key] ?? 0}</strong>
            <span>{label}</span>
          </article>
        ))}
      </div>
      <button className="launch-button" onClick={onLaunch} disabled={isLaunching}>
        {isLaunching ? "Launching..." : "Launch Autonomous Cleanup"}
      </button>
      <p className="microcopy">Agent will act on the open web, phone network, control plane, and database.</p>
    </section>
  );
}
