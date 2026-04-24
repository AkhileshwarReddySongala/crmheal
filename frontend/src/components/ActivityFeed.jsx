import { Database, Globe, Phone, Radar, Shield } from "lucide-react";

function iconFor(source = "") {
  if (source.includes("vapi")) return Phone;
  if (source.includes("tinyfish")) return Globe;
  if (source.includes("guild")) return Shield;
  if (source.includes("ghost")) return Database;
  return Radar;
}

export function ActivityFeed({ events, connected, error }) {
  return (
    <aside className="activity">
      <div className="activity-head">
        <h2>Activity Feed</h2>
        <span className={connected ? "live" : "polling"}>{connected ? "SSE live" : "Polling"}</span>
      </div>
      {error && <div className="feed-error">{error}</div>}
      <div className="feed-list">
        {events.length === 0 && <p className="muted">Waiting for agent events...</p>}
        {events.map((event, index) => {
          const Icon = iconFor(event.source || event.type);
          return (
            <div className="feed-item" key={`${event.timestamp}-${index}`}>
              <Icon size={16} />
              <div>
                <span className="mono">{event.timestamp?.split("T")[1]?.replace("Z", "")}</span>
                <p>{event.message || event.action || event.type}</p>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
