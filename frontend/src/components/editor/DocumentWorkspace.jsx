import { Link } from "react-router";
import useCollaboration from "../../hooks/useCollaboration.js";
import CollaborativeEditor from "./CollaborativeEditor.jsx";
import ConnectionBadge from "./ConnectionBadge.jsx";

/** Mounted only after the REST API confirmed we may open this document. */
export default function DocumentWorkspace({ documentId }) {
  const { ydoc, status, synced, fatalError } = useCollaboration(documentId);

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
      </div>
      {ydoc && <CollaborativeEditor key={documentId} ydoc={ydoc} synced={synced} />}
    </>
  );
}
