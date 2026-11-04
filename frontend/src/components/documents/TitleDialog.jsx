import { useEffect, useState } from "react";
import Button from "../ui/Button.jsx";
import Modal from "../ui/Modal.jsx";
import TextField from "../ui/TextField.jsx";
import { TITLE_MAX_LENGTH } from "../../services/documents.js";

/**
 * Used for both "new document" and "rename document".
 * `onSubmit(title)` must return a promise; errors are shown inside the dialog.
 */
export default function TitleDialog({
  open,
  heading,
  submitLabel,
  initialTitle = "",
  allowEmpty = false,
  onSubmit,
  onClose,
}) {
  const [title, setTitle] = useState(initialTitle);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle(initialTitle);
      setError("");
      setBusy(false);
    }
  }, [open, initialTitle]);

  async function handleSubmit(event) {
    event.preventDefault();
    const clean = title.trim();
    if (!clean && !allowEmpty) return setError("العنوان لا يمكن أن يكون فارغًا.");
    if (clean.length > TITLE_MAX_LENGTH) return setError(`العنوان طويل جدًا (${TITLE_MAX_LENGTH} حرف كحد أقصى).`);

    setBusy(true);
    try {
      await onSubmit(clean);
    } catch (err) {
      setError(err.fieldErrors?.title || err.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      title={heading}
      onClose={onClose}
      busy={busy}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            إلغاء
          </Button>
          <Button type="submit" form="title-dialog-form" loading={busy}>
            {submitLabel}
          </Button>
        </>
      }
    >
      <form id="title-dialog-form" onSubmit={handleSubmit} noValidate>
        <TextField
          label="عنوان المستند"
          value={title}
          maxLength={TITLE_MAX_LENGTH + 1}
          placeholder={allowEmpty ? "مستند بلا عنوان" : ""}
          onChange={(e) => {
            setTitle(e.target.value);
            setError("");
          }}
          error={error}
        />
      </form>
    </Modal>
  );
}
