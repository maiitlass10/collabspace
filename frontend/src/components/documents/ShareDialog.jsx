import { useEffect, useState } from "react";
import { useToast } from "../../context/ToastContext.jsx";
import { documentsApi, ROLE_LABELS } from "../../services/documents.js";
import Avatar from "../ui/Avatar.jsx";
import Button from "../ui/Button.jsx";
import Modal from "../ui/Modal.jsx";
import Spinner from "../ui/Spinner.jsx";
import TextField from "../ui/TextField.jsx";

function RoleSelect({ value, onChange, disabled, label }) {
  return (
    <select
      className="field-input role-select"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-label={label}
    >
      <option value="editor">{ROLE_LABELS.editor} · يكتب ويعدّل</option>
      <option value="viewer">{ROLE_LABELS.viewer} · يشاهد فقط</option>
    </select>
  );
}

function PersonRow({ user, children }) {
  return (
    <li className="member-row">
      <Avatar name={user.display_name} color={user.color} size={36} />
      <div className="member-info">
        <span className="member-name">{user.display_name}</span>
        <bdi className="member-email" dir="ltr">
          {user.email}
        </bdi>
      </div>
      <div className="member-actions">{children}</div>
    </li>
  );
}

/** Owner-only dialog: invite people by email and manage their roles. */
export default function ShareDialog({ open, doc, onClose }) {
  const toast = useToast();
  const [data, setData] = useState(null); // { owner, members }
  const [loadError, setLoadError] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("editor");
  const [errors, setErrors] = useState({});
  const [sending, setSending] = useState(false);
  const [busyMember, setBusyMember] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setData(null);
    setLoadError("");
    setEmail("");
    setErrors({});
    documentsApi
      .members(doc.id)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setLoadError(err.message));
    return () => {
      cancelled = true;
    };
  }, [open, doc.id]);

  async function handleShare(event) {
    event.preventDefault();
    const clean = email.trim();
    if (!clean) return setErrors({ email: "أدخل البريد الإلكتروني للشخص." });
    setSending(true);
    setErrors({});
    try {
      const member = await documentsApi.share(doc.id, clean, role);
      setData((d) => ({ ...d, members: [...d.members, member] }));
      setEmail("");
      toast.success(`تمت مشاركة المستند مع ${member.user.display_name}.`);
    } catch (err) {
      setErrors({ email: err.fieldErrors?.email || err.fieldErrors?.role || err.message });
    } finally {
      setSending(false);
    }
  }

  async function handleRoleChange(member, newRole) {
    setBusyMember(member.id);
    try {
      const updated = await documentsApi.changeRole(doc.id, member.id, newRole);
      setData((d) => ({ ...d, members: d.members.map((m) => (m.id === updated.id ? updated : m)) }));
      toast.success(`${member.user.display_name} أصبح ${ROLE_LABELS[newRole]}.`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusyMember(null);
    }
  }

  async function handleRemove(member) {
    setBusyMember(member.id);
    try {
      await documentsApi.removeMember(doc.id, member.id);
      setData((d) => ({ ...d, members: d.members.filter((m) => m.id !== member.id) }));
      toast.success(`تمت إزالة ${member.user.display_name}.`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusyMember(null);
    }
  }

  return (
    <Modal open={open} title={`مشاركة «${doc.title}»`} onClose={onClose}>
      <form className="share-form" onSubmit={handleShare} noValidate>
        <TextField
          label="البريد الإلكتروني"
          type="email"
          dir="ltr"
          placeholder="name@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setErrors({});
          }}
          error={errors.email}
          hint="يجب أن يكون لدى الشخص حساب في CollabSpace."
        />
        <div className="share-form-row">
          <RoleSelect value={role} onChange={setRole} disabled={sending} label="الدور" />
          <Button type="submit" loading={sending}>
            مشاركة
          </Button>
        </div>
      </form>

      <h3 className="share-section-title">لديهم وصول</h3>
      {loadError && <p className="field-error">{loadError}</p>}
      {!data && !loadError && (
        <div className="text-center">
          <Spinner size={24} />
        </div>
      )}
      {data && (
        <ul className="member-list">
          <PersonRow user={data.owner}>
            <span className="role-badge role-badge--owner">{ROLE_LABELS.owner}</span>
          </PersonRow>
          {data.members.map((member) => (
            <PersonRow key={member.id} user={member.user}>
              <RoleSelect
                value={member.role}
                onChange={(newRole) => handleRoleChange(member, newRole)}
                disabled={busyMember === member.id}
                label={`دور ${member.user.display_name}`}
              />
              <button
                type="button"
                className="icon-btn icon-btn--danger"
                onClick={() => handleRemove(member)}
                disabled={busyMember === member.id}
                aria-label={`إزالة ${member.user.display_name}`}
                title="إزالة"
              >
                ×
              </button>
            </PersonRow>
          ))}
          {data.members.length === 0 && <li className="muted member-empty">لم تشارك هذا المستند مع أحد بعد.</li>}
        </ul>
      )}
    </Modal>
  );
}
