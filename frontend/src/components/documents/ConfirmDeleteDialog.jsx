import { useEffect, useState } from "react";
import Button from "../ui/Button.jsx";
import Modal from "../ui/Modal.jsx";

export default function ConfirmDeleteDialog({ doc, onConfirm, onClose }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setBusy(false);
    setError("");
  }, [doc]);

  async function handleConfirm() {
    setBusy(true);
    try {
      await onConfirm(doc);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      open={Boolean(doc)}
      title="حذف المستند"
      onClose={onClose}
      busy={busy}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            إلغاء
          </Button>
          <Button variant="danger" onClick={handleConfirm} loading={busy}>
            حذف نهائيًا
          </Button>
        </>
      }
    >
      <p>
        هل أنت متأكد من حذف المستند <strong>«{doc?.title}»</strong>؟
      </p>
      <p className="muted small">لا يمكن التراجع عن هذا الإجراء.</p>
      {error && <p className="field-error">{error}</p>}
    </Modal>
  );
}
