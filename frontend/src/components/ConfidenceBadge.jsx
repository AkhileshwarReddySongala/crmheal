export function ConfidenceBadge({ confidence = 0 }) {
  const label = confidence >= 85 ? "Auto-merge" : confidence >= 60 ? "Review" : "Needs human";
  const tone = confidence >= 85 ? "green" : confidence >= 60 ? "amber" : "red";
  return <span className={`confidence ${tone}`}>{confidence}% {label}</span>;
}
