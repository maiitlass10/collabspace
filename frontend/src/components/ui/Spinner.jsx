export default function Spinner({ size = 20, label = "جارٍ التحميل…" }) {
  return (
    <span className="spinner" role="status" style={{ width: size, height: size }}>
      <span className="visually-hidden">{label}</span>
    </span>
  );
}

export function FullPageLoader() {
  return (
    <div className="full-page-center">
      <Spinner size={36} />
    </div>
  );
}
