export function AuditLog({ events, ghostStats }) {
  const guildWorkspaceUrl =
    import.meta.env.VITE_GUILD_WORKSPACE_URL ||
    import.meta.env.GUILD_WORKSPACE_URL ||
    "https://app.guild.ai/users/akhileshwar.songala/workspaces/zxc";
  const guildAgentName = import.meta.env.VITE_GUILD_AGENT_NAME || import.meta.env.GUILD_AGENT_NAME || "crm-heal";

  return (
    <section className="bottom-panel">
      <div>
        <h3>Audit Log</h3>
        <div className="audit-list">
          {events.filter((event) => event.type === "audit_event").slice(0, 8).map((event, index) => (
            <div className="audit-row" key={index}>
              <span className="mono">{event.agent}</span>
              <strong>{event.action}</strong>
              <span>{event.source || event.mode}</span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h3>Guild.ai Control Plane</h3>
        <p className="badge-line">Linked to Guild.ai</p>
        <p className="muted">{guildAgentName}</p>
        <a href={guildWorkspaceUrl} target="_blank" rel="noreferrer">Open Guild Workspace</a>
        <ul className="setup-list" aria-label="Guild setup status">
          <li>CLI installed</li>
          <li>Authenticated</li>
          <li>Agent initialized</li>
          <li>Agent published</li>
        </ul>
      </div>
      <div>
        <h3>Ghost DB</h3>
        {ghostStats?.type === "ghost_persisted" ? (
          <p className="badge-line">Persisted {ghostStats.total} rows, {ghostStats.verified} verified, avg {ghostStats.avg_confidence}%</p>
        ) : ghostStats?.type === "ghost_skipped" ? (
          <p className="badge-line">Ghost skipped</p>
        ) : ghostStats?.type === "ghost_failed" ? (
          <p className="badge-line">Ghost failed</p>
        ) : (
          <p className="muted">Waiting for batch completion...</p>
        )}
      </div>
    </section>
  );
}
