import { useEffect, useState } from "react";

/**
 * Who is in the document right now, read from the Yjs "awareness" states.
 *
 * The `user` field of every state ({ id, name, color }) is set by the SERVER
 * from the logged-in account, so it can be trusted for display.
 * The same account in two tabs counts as one person (with `connections: 2`).
 */
function collectUsers(awareness, currentUserId) {
  const byUser = new Map();
  awareness.getStates().forEach((state) => {
    const user = state?.user;
    if (!user || user.id == null) return;
    const entry = byUser.get(user.id);
    if (entry) {
      entry.connections += 1;
      return;
    }
    byUser.set(user.id, {
      id: user.id,
      name: user.name || "؟",
      color: user.color,
      connections: 1,
      isSelf: user.id === currentUserId,
    });
  });
  // Me first, then everyone else alphabetically.
  return [...byUser.values()].sort(
    (a, b) => Number(b.isSelf) - Number(a.isSelf) || a.name.localeCompare(b.name, "ar")
  );
}

export default function usePresence(provider, currentUserId) {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    if (!provider) return undefined;
    const { awareness } = provider;
    const update = () => setUsers(collectUsers(awareness, currentUserId));
    update();
    // "change" fires only when someone joins, leaves or changes (not on heartbeats).
    awareness.on("change", update);
    return () => awareness.off("change", update);
  }, [provider, currentUserId]);

  return users;
}
