import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useToast } from "../context/ToastContext.jsx";
import Button from "../components/ui/Button.jsx";
import { FullPageLoader } from "../components/ui/Spinner.jsx";
import ConfirmDeleteDialog from "../components/documents/ConfirmDeleteDialog.jsx";
import ShareDialog from "../components/documents/ShareDialog.jsx";
import { canEdit, documentsApi, isOwner, ROLE_LABELS, TITLE_MAX_LENGTH } from "../services/documents.js";
import { fullDate, timeAgo } from "../utils/date.js";
import Spinner from "../components/ui/Spinner.jsx";

// The editor (Tiptap + Yjs) is large: download it only when a document is opened.
const DocumentWorkspace = lazy(() => import("../components/editor/DocumentWorkspace.jsx"));

export default function DocumentPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();

  const [doc, setDoc] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | notfound | error
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [saveState, setSaveState] = useState("idle"); // idle | saving | saved | error
  const [deleting, setDeleting] = useState(null);
  const [sharing, setSharing] = useState(false);
  // Changing this remounts the editor = a fresh WebSocket with the new role.
  const [connectionKey, setConnectionKey] = useState(0);
  const titleInput = useRef(null);
  // The role we had before the server told us it changed.
  const roleRef = useRef(null);
  useEffect(() => {
    roleRef.current = doc?.role ?? null;
  }, [doc]);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    documentsApi
      .get(id)
      .then((data) => {
        if (cancelled) return;
        setDoc(data);
        setTitle(data.title);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setStatus(err.status === 404 ? "notfound" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  // The server closed our editor connection because our access changed.
  const handleAccessChanged = useCallback(async () => {
    try {
      const data = await documentsApi.get(id);
      if (roleRef.current && roleRef.current !== data.role) {
        toast.success(`تغيّرت صلاحيتك: أصبحت ${ROLE_LABELS[data.role]}.`);
      }
      setDoc(data);
      setTitle(data.title);
      setConnectionKey((k) => k + 1);
    } catch (err) {
      if (err.status === 404) {
        toast.error("لم يعد لديك وصول إلى هذا المستند.");
        setStatus("notfound");
      } else {
        setError(err.message);
        setStatus("error");
      }
    }
  }, [id, toast]);

  async function saveTitle() {
    if (!canEdit(doc.role)) return;
    const clean = title.trim().replace(/\s+/g, " ");
    if (clean === doc.title) {
      setTitle(doc.title);
      return;
    }
    if (!clean) {
      toast.error("العنوان لا يمكن أن يكون فارغًا.");
      setTitle(doc.title);
      return;
    }
    setSaveState("saving");
    try {
      const updated = await documentsApi.rename(doc.id, clean);
      setDoc(updated);
      setTitle(updated.title);
      setSaveState("saved");
    } catch (err) {
      setSaveState("error");
      setTitle(doc.title);
      toast.error(err.fieldErrors?.title || err.message);
    }
  }

  async function handleDelete(target) {
    await documentsApi.remove(target.id);
    toast.success("تم حذف المستند.");
    navigate("/", { replace: true });
  }

  if (status === "loading") return <FullPageLoader />;

  if (status === "notfound" || status === "error") {
    return (
      <div className="page-container">
        <section className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">
            {status === "notfound" ? "🔒" : "⚠️"}
          </div>
          <h2>{status === "notfound" ? "المستند غير موجود" : "تعذّر فتح المستند"}</h2>
          <p className="muted">
            {status === "notfound" ? "ربما حُذف المستند، أو ليست لديك صلاحية الوصول إليه." : error}
          </p>
          <Link to="/" className="btn btn-primary">
            العودة إلى مستنداتي
          </Link>
        </section>
      </div>
    );
  }

  const saveLabel = {
    idle: `آخر تعديل ${timeAgo(doc.updated_at)}`,
    saving: "جارٍ الحفظ…",
    saved: "تم الحفظ ✓",
    error: "لم يتم الحفظ",
  }[saveState];

  const owner = isOwner(doc.role);
  const editable = canEdit(doc.role);

  return (
    <div className="page-container">
      <nav className="breadcrumb" aria-label="مسار التنقل">
        {owner ? <Link to="/">مستنداتي</Link> : <Link to="/?tab=shared">مشتركة معي</Link>}
        <span aria-hidden="true">‹</span>
        <span className="breadcrumb-current">{doc.title}</span>
      </nav>

      <header className="doc-header">
        <input
          ref={titleInput}
          className="doc-title-input"
          aria-label="عنوان المستند"
          value={title}
          readOnly={!editable}
          title={editable ? undefined : "لا يمكنك تغيير العنوان"}
          maxLength={TITLE_MAX_LENGTH}
          onChange={(e) => {
            setTitle(e.target.value);
            setSaveState("idle");
          }}
          onBlur={saveTitle}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
            if (e.key === "Escape") {
              setTitle(doc.title);
              setTimeout(() => e.target.blur());
            }
          }}
        />
        <div className="doc-header-actions">
          <span className={`save-state save-state--${saveState}`} title={fullDate(doc.updated_at)}>
            {saveLabel}
          </span>
          {owner ? (
            <>
              <Button onClick={() => setSharing(true)}>مشاركة</Button>
              <Button variant="danger-outline" onClick={() => setDeleting(doc)}>
                حذف
              </Button>
            </>
          ) : (
            <span className="shared-by">
              مشارك من <strong>{doc.owner.display_name}</strong>
              <span className={`role-badge role-badge--${doc.role}`}>{ROLE_LABELS[doc.role]}</span>
            </span>
          )}
        </div>
      </header>

      <Suspense
        fallback={
          <div className="editor-shell editor-fallback">
            <Spinner size={28} />
          </div>
        }
      >
        <DocumentWorkspace
          key={`${doc.id}:${connectionKey}`}
          documentId={doc.id}
          readOnly={!editable}
          onAccessChanged={handleAccessChanged}
        />
      </Suspense>

      <ConfirmDeleteDialog doc={deleting} onConfirm={handleDelete} onClose={() => setDeleting(null)} />
      {owner && <ShareDialog open={sharing} doc={doc} onClose={() => setSharing(false)} />}
    </div>
  );
}
