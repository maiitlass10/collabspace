const COLORS = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed", "#dc2626"];

/** A stable color per name, so each user always gets the same color. */
function colorFor(name = "") {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
  return COLORS[hash % COLORS.length];
}

/** `color` comes from the server (user.color); fall back to a name-based one. */
export default function Avatar({ name = "", size = 36, color }) {
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, background: color || colorFor(name), fontSize: size * 0.42 }}
      title={name}
      aria-hidden="true"
    >
      {initial}
    </span>
  );
}
