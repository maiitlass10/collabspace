import { useCallback, useEffect, useState } from "react";
import * as Y from "yjs";
import { useToast } from "../../context/ToastContext.jsx";
import { documentsApi } from "../../services/documents.js";
import { fullDate, timeAgo } from "../../utils/date.js";
import Button from "../ui/Button.jsx";
import Modal from "../ui/Modal.jsx";
import Spinner from "../ui/Spinner.jsx";
import TextField from "../ui/TextField.jsx";
import VersionPreview from "./VersionPreview.jsx";

const versionName = (v) => v.label || `إصدار ${fullDate(v.created_at)}`;

// The server rejects request bodies over ~2.5 MB.
const MAX_STATE_CHARS = 2_000_000;

/**
 * Our full Yjs state, sent along with "save version" / "restore". The last
 * keystrokes may still be on their way over the WebSocket; the server merges
 * this state first, so the snapshot really contains what we see.
 */
function snapshotBody(ydoc) {
  if (!ydoc) return {};
  const bytes = Y.encodeStateAsUpdate(ydoc);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  const encoded = btoa(binary);
  return encoded.length <= MAX_STATE_CHARS ? { browser_state: encoded } : {};
}

/**
 * Saved versions of a document:
 *  - editors can save the current content as a named version
 *  - everyone can preview a version (read-only)
 *  - editors can restore one (a backup of the current content is saved first)
 */
export default function VersionsPanel({ open, documentId, canEdit, editor, ydoc, onClose }) {
  const toast = useToast();
  const [versions, setVersions] = useState(null);
  const [error, setError] = useState("");
  const [label, setLabel] = useState("");
  const [labelError, setLabelError] = useState("");
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(null); // version with `state`
  const [previewEditor, setPreviewEditor] = useState(null);
  const [restoring, setRestoring] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      setVersions(await documentsApi.versions(documentId));
    } catch (err) {
      setError(err.message);
    }
  }, [documentId]);

  useEffect(() => {
    if (!open) return;
    setVersions(null);
    setPreview(null);
    setLabel("");
    setLabelError("");
    load();
  }, [open, load]);

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setLabelError("");
    try {
      const version = await documentsApi.saveVersion(documentId, label.trim(), snapshotBody(ydoc));
      setVersions((list) => [version, ...(list || [])]);
      setLabel("");
      toast.success("تم حفظ الإصدار.");
    } catch (err) {
      setLabelError(err.fieldErrors?.label || err.message);
    } finally {
      setSaving(false);
    }
  }

  async function openPreview(version) {
    try {
      setPreview(await documentsApi.version(documentId, version.id));
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function handleRestore() {
    if (!editor || !previewEditor) return;
    setRestoring(true);
    try {
      // 1) The server saves a backup of the current content and logs the restore.
      await documentsApi.restoreVersion(documentId, preview.id, snapshotBody(ydoc));
      // 2) Put the old content into the LIVE editor. Yjs turns this into normal
      //    edits, so every connected user sees it and the server saves it.
      editor.commands.setContent(previewEditor.getJSON());
      toast.success("تم استرجاع الإصدار. حُفظت نسخة احتياطية من المحتوى السابق.");
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRestoring(false);
    }
  }

  const title = preview ? `معاينة: ${versionName(preview)}` : "الإصدارات";

  return (
    <Modal open={open} title={title} onClose={onClose} busy={restoring} size={preview ? "wide" : "normal"}>
      {preview ? (
        <>
          <p className="muted version-meta">
            حفظه {preview.created_by?.display_name || "مستخدم محذوف"} · {fullDate(preview.created_at)}
          </p>
          <div className="version-preview-frame">
            <VersionPreview state={preview.state} onReady={setPreviewEditor} />
          </div>
          <div className="version-actions">
            <Button variant="secondary" onClick={() => setPreview(null)} disabled={restoring}>
              → رجوع إلى القائمة
            </Button>
            {canEdit && (
              <Button onClick={handleRestore} loading={restoring} disabled={!editor || !previewEditor}>
                استرجاع هذا الإصدار
              </Button>
            )}
          </div>
        </>
      ) : (
        <>
          {canEdit && (
            <form className="version-save" onSubmit={handleSave} noValidate>
              <TextField
                label="حفظ المحتوى الحالي كإصدار"
                placeholder="اسم اختياري، مثل: المسودة الأولى"
                value={label}
                maxLength={101}
                onChange={(e) => {
                  setLabel(e.target.value);
                  setLabelError("");
                }}
                error={labelError}
              />
              <Button type="submit" loading={saving}>
                حفظ إصدار
              </Button>
            </form>
          )}

          {error && <p className="field-error">{error}</p>}
          {!versions && !error && (
            <div className="text-center">
              <Spinner size={24} />
            </div>
          )}
          {versions && versions.length === 0 && <p className="muted">لا توجد إصدارات محفوظة بعد.</p>}
          {versions && versions.length > 0 && (
            <ul className="version-list">
              {versions.map((v) => (
                <li key={v.id}>
                  <button type="button" className="version-item" onClick={() => openPreview(v)}>
                    <span className="version-name">
                      {v.kind === "backup" ? "🛟 " : "💾 "}
                      {versionName(v)}
                    </span>
                    <span className="version-info" title={fullDate(v.created_at)}>
                      {v.created_by?.display_name || "مستخدم محذوف"} · {timeAgo(v.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Modal>
  );
}
