import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useToast } from "../context/ToastContext.jsx";
import Button from "../components/ui/Button.jsx";
import { FullPageLoader } from "../components/ui/Spinner.jsx";
import ConfirmDeleteDialog from "../components/documents/ConfirmDeleteDialog.jsx";
import { documentsApi, TITLE_MAX_LENGTH } from "../services/documents.js";
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
  const titleInput = useRef(null);

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

  async function saveTitle() {
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

  return (
    <div className="page-container">
      <nav className="breadcrumb" aria-label="مسار التنقل">
        <Link to="/">مستنداتي</Link>
        <span aria-hidden="true">‹</span>
        <span className="breadcrumb-current">{doc.title}</span>
      </nav>

      <header className="doc-header">
        <input
          ref={titleInput}
          className="doc-title-input"
          aria-label="عنوان المستند"
          value={title}
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
          <Button variant="danger-outline" onClick={() => setDeleting(doc)}>
            حذف
          </Button>
        </div>
      </header>

      <Suspense
        fallback={
          <div className="editor-shell editor-fallback">
            <Spinner size={28} />
          </div>
        }
      >
        <DocumentWorkspace documentId={doc.id} />
      </Suspense>

      <ConfirmDeleteDialog doc={deleting} onConfirm={handleDelete} onClose={() => setDeleting(null)} />
    </div>
  );
}
