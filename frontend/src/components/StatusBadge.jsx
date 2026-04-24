const labels = {
  QUEUED: "Queued",
  SEARCHING_WEB: "Searching Web",
  PARSING_DOM: "Parsing DOM",
  NEEDS_VERIFICATION: "Needs Call",
  CALLING_LEAD: "Calling Lead",
  CALL_PENDING: "Call Pending",
  CALL_TIMEOUT: "Call Timeout",
  VERIFIED: "Verified",
  COMPLETED: "Complete",
  FAILED: "Failed"
};

export function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{labels[status] || status}</span>;
}
