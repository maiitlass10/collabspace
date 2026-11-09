import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { canEdit, isOwner, ROLE_LABELS } from "../../services/documents.js";
import { fullDate, timeAgo } from "../../utils/date.js";

export default function DocumentCard({ doc, onRename, onDelete }) {
  const owner = isOwner(doc.role);
  const mayRename = canEdit(doc.role);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Close the menu when clicking anywhere else.
  useEffect(() => {
    if (!menuOpen) return undefined;
    function onClick(event) {
      if (!menuRef.current?.contains(event.target)) setMenuOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  return (
    <article className="doc-card">
      <Link to={`/documents/${doc.id}`} className="doc-card-link">
        <div className="doc-card-thumb" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <h3 className="doc-card-title" title={doc.title}>
          {doc.title}
        </h3>
        <p className="doc-card-meta" title={fullDate(doc.updated_at)}>
          آخر تعديل {timeAgo(doc.updated_at)}
        </p>
        {!owner && (
          <p className="doc-card-shared">
            <span>من {doc.owner.display_name}</span>
            <span className={`role-badge role-badge--${doc.role}`}>{ROLE_LABELS[doc.role]}</span>
          </p>
        )}
      </Link>

      {mayRename && (
        <div className="doc-card-menu" ref={menuRef}>
          <button
            type="button"
            className="icon-btn"
            aria-label={`خيارات المستند ${doc.title}`}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            ⋮
          </button>
          {menuOpen && (
            <div className="dropdown" role="menu">
              <button
                type="button"
                role="menuitem"
                className="dropdown-item"
                onClick={() => {
                  setMenuOpen(false);
                  onRename(doc);
                }}
              >
                إعادة تسمية
              </button>
              {owner && (
                <button
                  type="button"
                  role="menuitem"
                  className="dropdown-item dropdown-item--danger"
                  onClick={() => {
                    setMenuOpen(false);
                    onDelete(doc);
                  }}
                >
                  حذف
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

export function DocumentCardSkeleton() {
  return (
    <div className="doc-card doc-card--skeleton" aria-hidden="true">
      <div className="skeleton skeleton-thumb" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-line skeleton-line--short" />
    </div>
  );
}
