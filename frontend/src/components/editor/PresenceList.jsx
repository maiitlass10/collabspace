import Avatar from "../ui/Avatar.jsx";

const MAX_VISIBLE = 5;

function describe(user) {
  let text = user.name;
  if (user.isSelf) text += " (أنت)";
  if (user.connections > 1) text += ` · مفتوح في ${user.connections} نوافذ`;
  return text;
}

/** Colored avatars of everyone currently in the document. */
export default function PresenceList({ users }) {
  if (users.length === 0) return null;

  const visible = users.slice(0, MAX_VISIBLE);
  const hidden = users.slice(MAX_VISIBLE);
  const alone = users.length === 1 && users[0].isSelf;

  return (
    <div className="presence" aria-live="polite">
      <span className="presence-label">{alone ? "أنت وحدك هنا الآن" : `${users.length} متصلون الآن`}</span>
      <ul className="presence-list" aria-label="المتصلون الآن">
        {visible.map((user) => (
          <li
            key={user.id}
            className={`presence-item ${user.isSelf ? "presence-item--self" : ""}`}
            style={{ "--presence-color": user.color }}
            title={describe(user)}
          >
            <Avatar name={user.name} color={user.color} size={32} />
            {user.connections > 1 && (
              <span className="presence-count" aria-hidden="true">
                {user.connections}
              </span>
            )}
            <span className="visually-hidden">{describe(user)}</span>
          </li>
        ))}
        {hidden.length > 0 && (
          <li className="presence-item presence-more" title={hidden.map(describe).join("، ")}>
            +{hidden.length}
          </li>
        )}
      </ul>
    </div>
  );
}
