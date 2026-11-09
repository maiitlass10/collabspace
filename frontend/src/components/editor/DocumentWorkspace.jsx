import { useState } from "react";
import { Link } from "react-router";
import { useAuth } from "../../context/AuthContext.jsx";
import useCollaboration from "../../hooks/useCollaboration.js";
import usePresence from "../../hooks/usePresence.js";
import CollaborativeEditor from "./CollaborativeEditor.jsx";
import ConnectionBadge from "./ConnectionBadge.jsx";
import PresenceList from "./PresenceList.jsx";
import ActivityPanel from "./ActivityPanel.jsx";
import VersionsPanel from "./VersionsPanel.jsx";

/** Mounted only after the REST API confirmed we may open this document. */
export default function DocumentWorkspace({ documentId, readOnly = false, onAccessChanged }) {
  const { user } = useAuth();
  const { ydoc, provider, status, synced, fatalError } = useCollaboration(documentId, onAccessChanged);
  const users = usePresence(provider, user.id);
  const [editor, setEditor] = useState(null);
  const [panel, setPanel] = useState(null); // "activity" | "versions" | null

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
        <div className="workspace-status">
          <ConnectionBadge status={status} />
          {readOnly && <span className="readonly-badge">👁 للقراءة فقط</span>}
        </div>
        <div className="workspace-actions">
          {status === "connected" && <PresenceList users={users} />}
          <button type="button" className="chip-btn" onClick={() => setPanel("activity")}>
            🕒 النشاط
          </button>
          <button type="button" className="chip-btn" onClick={() => setPanel("versions")}>
            💾 الإصدارات
          </button>
        </div>
      </div>
      {ydoc && provider && (
        <CollaborativeEditor
          key={documentId}
          ydoc={ydoc}
          provider={provider}
          user={user}
          synced={synced}
          readOnly={readOnly}
          onReady={setEditor}
        />
      )}

      <ActivityPanel open={panel === "activity"} documentId={documentId} onClose={() => setPanel(null)} />
      <VersionsPanel
        open={panel === "versions"}
        documentId={documentId}
        canEdit={!readOnly && synced}
        editor={editor}
        ydoc={ydoc}
        onClose={() => setPanel(null)}
      />
    </>
  );
}
