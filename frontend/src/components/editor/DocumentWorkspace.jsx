import { Link } from "react-router";
import { useAuth } from "../../context/AuthContext.jsx";
import useCollaboration from "../../hooks/useCollaboration.js";
import usePresence from "../../hooks/usePresence.js";
import CollaborativeEditor from "./CollaborativeEditor.jsx";
import ConnectionBadge from "./ConnectionBadge.jsx";
import PresenceList from "./PresenceList.jsx";

/** Mounted only after the REST API confirmed we may open this document. */
export default function DocumentWorkspace({ documentId }) {
  const { user } = useAuth();
  const { ydoc, provider, status, synced, fatalError } = useCollaboration(documentId);
  const users = usePresence(provider, user.id);

  if (fatalError) {
    return (
      <section className="empty-state">
        <div className="empty-state-icon" aria-hidden="true">
          🔒
        </div>
        <h2>تعذّر فتح المحرر</h2>
        <p className="muted">{fatalError}</p>
        <Link to="/" className="btn btn-primary">
          العودة إلى مستنداتي
        </Link>
      </section>
    );
  }

  return (
    <>
      <div className="workspace-bar">
        <ConnectionBadge status={status} />
        {status === "connected" && <PresenceList users={users} />}
      </div>
      {ydoc && provider && (
        <CollaborativeEditor key={documentId} ydoc={ydoc} provider={provider} user={user} synced={synced} />
      )}
    </>
  );
}
