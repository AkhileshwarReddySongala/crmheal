import { PhoneCall } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

export function DataTable({ jobs, onVerify }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Company</th>
            <th>Title</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Status</th>
            <th>Confidence</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const row = job.original;
            const enriched = job.enriched || {};
            const canVerify = row.phone && ["NEEDS_VERIFICATION", "CALL_TIMEOUT"].includes(job.status);
            return (
              <tr key={job.job_id}>
                <td className="mono">{job.record_id}</td>
                <td>{row.first_name} {row.last_name}</td>
                <td>{row.company || "Unknown"}</td>
                <td className={enriched.job_title ? "changed" : ""}>{enriched.job_title || row.title || "Missing"}</td>
                <td className={enriched.email ? "changed" : ""}>{enriched.email || row.email || "Missing"}</td>
                <td>{row.phone || "Missing"}</td>
                <td><StatusBadge status={job.status} /></td>
                <td><ConfidenceBadge confidence={job.confidence || 0} /></td>
                <td>
                  {canVerify ? (
                    <button className="icon-action" onClick={() => onVerify(job.job_id)} title="Verify via call">
                      <PhoneCall size={16} /> Verify
                    </button>
                  ) : (
                    <span className="muted">-</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
