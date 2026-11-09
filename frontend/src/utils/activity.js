import { ROLE_LABELS } from "../services/documents.js";

const ICONS = {
  created: "✨",
  renamed: "✏️",
  edited: "📝",
  shared: "🤝",
  role_changed: "🔁",
  unshared: "🚫",
  left: "👋",
  version_saved: "💾",
  version_restored: "⏪",
};

/** Turn an activity entry from the API into an icon + an Arabic sentence. */
export function describeActivity({ action, metadata = {} }) {
  const target = metadata.target?.display_name || "مستخدم";
  const role = (r) => ROLE_LABELS[r] || r;
  const text = {
    created: "أنشأ المستند",
    renamed: `غيّر العنوان من «${metadata.from}» إلى «${metadata.to}»`,
    edited: "عدّل المحتوى",
    shared: `شارك المستند مع ${target} (${role(metadata.role)})`,
    role_changed: `غيّر دور ${target} من ${role(metadata.from)} إلى ${role(metadata.to)}`,
    unshared: `أزال ${target} من المستند`,
    left: "غادر المستند",
    version_saved: metadata.label ? `حفظ إصدارًا باسم «${metadata.label}»` : "حفظ إصدارًا",
    version_restored: `استرجع الإصدار «${metadata.label}»`,
  }[action];
  return { icon: ICONS[action] || "•", text: text || action };
}
