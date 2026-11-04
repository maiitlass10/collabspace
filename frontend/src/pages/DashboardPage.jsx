import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Alert from "../components/ui/Alert.jsx";
import Button from "../components/ui/Button.jsx";
import ConfirmDeleteDialog from "../components/documents/ConfirmDeleteDialog.jsx";
import DocumentCard, { DocumentCardSkeleton } from "../components/documents/DocumentCard.jsx";
import TitleDialog from "../components/documents/TitleDialog.jsx";
import useDebouncedValue from "../hooks/useDebouncedValue.js";
import { documentsApi } from "../services/documents.js";
import { documentsCount } from "../utils/date.js";

export default function DashboardPage() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [documents, setDocuments] = useState([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState(null);
  const [deleting, setDeleting] = useState(null);

  // Ignore responses from outdated searches (user typed again meanwhile).
  const requestId = useRef(0);

  const load = useCallback(async (searchTerm, page = 1) => {
    const id = ++requestId.current;
    if (page === 1) setStatus("loading");
    else setLoadingMore(true);
    try {
      const data = await documentsApi.list({ search: searchTerm, page });
      if (id !== requestId.current) return;
      setDocuments((current) => (page === 1 ? data.results : [...current, ...data.results]));
      setCount(data.count);
      setNextPage(data.next ? page + 1 : null);
      setStatus("ready");
    } catch (err) {
      if (id !== requestId.current) return;
      if (page === 1) {
        setError(err.message);
        setStatus("error");
      } else {
        toast.error(err.message);
      }
    } finally {
      if (id === requestId.current) setLoadingMore(false);
    }
  }, [toast]);

  useEffect(() => {
    load(debouncedSearch);
  }, [debouncedSearch, load]);

  async function handleCreate(title) {
    const doc = await documentsApi.create(title);
    toast.success("تم إنشاء المستند.");
    navigate(`/documents/${doc.id}`);
  }

  async function handleRename(title) {
    const updated = await documentsApi.rename(renaming.id, title);
    // Renaming changes updated_at, so move the document to the top.
    setDocuments((list) => [updated, ...list.filter((d) => d.id !== updated.id)]);
    setRenaming(null);
    toast.success("تم تغيير العنوان.");
  }

  async function handleDelete(doc) {
    await documentsApi.remove(doc.id);
    setDocuments((list) => list.filter((d) => d.id !== doc.id));
    setCount((c) => c - 1);
    setDeleting(null);
    toast.success("تم حذف المستند.");
  }

  const isSearching = debouncedSearch.trim().length > 0;

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">أهلًا، {user.display_name} 👋</h1>
          <p className="muted">
            {status === "ready" && !isSearching
              ? count > 0
                ? `لديك ${documentsCount(count)}.`
                : "ابدأ بإنشاء مستندك الأول."
              : "مستنداتك في مكان واحد."}
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>＋ مستند جديد</Button>
      </header>

      {location.state?.welcome && (
        <Alert type="success">تم إنشاء حسابك وتسجيل دخولك بنجاح. مرحبًا بك في CollabSpace!</Alert>
      )}

      {(count > 0 || isSearching || search) && (
        <div className="search-box">
          <input
            type="search"
            className="field-input"
            placeholder="ابحث في عناوين المستندات…"
            aria-label="البحث في المستندات"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {status === "loading" && (
        <div className="doc-grid">
          {Array.from({ length: 6 }, (_, i) => (
            <DocumentCardSkeleton key={i} />
          ))}
        </div>
      )}

      {status === "error" && (
        <section className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">
            ⚠️
          </div>
          <h2>تعذّر تحميل المستندات</h2>
          <p className="muted">{error}</p>
          <Button variant="secondary" onClick={() => load(debouncedSearch)}>
            إعادة المحاولة
          </Button>
        </section>
      )}

      {status === "ready" && documents.length === 0 && !isSearching && (
        <section className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">
            📄
          </div>
          <h2>لا توجد مستندات بعد</h2>
          <p className="muted">أنشئ مستندك الأول وابدأ الكتابة، ثم شاركه مع فريقك لاحقًا.</p>
          <Button onClick={() => setCreating(true)}>إنشاء أول مستند</Button>
        </section>
      )}

      {status === "ready" && documents.length === 0 && isSearching && (
        <section className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">
            🔍
          </div>
          <h2>لا توجد نتائج</h2>
          <p className="muted">لم نجد مستندًا عنوانه يحتوي «{debouncedSearch.trim()}».</p>
        </section>
      )}

      {status === "ready" && documents.length > 0 && (
        <>
          <div className="doc-grid">
            {documents.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} onRename={setRenaming} onDelete={setDeleting} />
            ))}
          </div>
          {nextPage && (
            <div className="text-center">
              <Button variant="secondary" loading={loadingMore} onClick={() => load(debouncedSearch, nextPage)}>
                عرض المزيد
              </Button>
            </div>
          )}
        </>
      )}

      <TitleDialog
        open={creating}
        heading="مستند جديد"
        submitLabel="إنشاء"
        allowEmpty
        onSubmit={handleCreate}
        onClose={() => setCreating(false)}
      />
      <TitleDialog
        open={Boolean(renaming)}
        heading="إعادة تسمية المستند"
        submitLabel="حفظ"
        initialTitle={renaming?.title || ""}
        onSubmit={handleRename}
        onClose={() => setRenaming(null)}
      />
      <ConfirmDeleteDialog doc={deleting} onConfirm={handleDelete} onClose={() => setDeleting(null)} />
    </div>
  );
}
