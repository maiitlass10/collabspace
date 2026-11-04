const LABELS = {
  connected: "متصل · يُحفظ تلقائيًا",
  connecting: "جارٍ الاتصال…",
  disconnected: "غير متصل · سيُعاد الاتصال تلقائيًا",
};

export default function ConnectionBadge({ status }) {
  return (
    <span className={`connection-badge connection-badge--${status}`} role="status" aria-live="polite">
      <span className="connection-dot" aria-hidden="true" />
      {LABELS[status] || status}
    </span>
  );
}
