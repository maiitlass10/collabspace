import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Button from "../components/ui/Button.jsx";
import TextField from "../components/ui/TextField.jsx";
import { authApi } from "../services/auth.js";

function ProfileForm() {
  const { user, updateUser } = useAuth();
  const toast = useToast();
  const [name, setName] = useState(user.display_name);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const clean = name.trim().replace(/\s+/g, " ");
  const unchanged = clean === user.display_name;

  async function handleSubmit(event) {
    event.preventDefault();
    if (clean.length < 2) return setError("الاسم يجب أن يكون حرفين على الأقل.");
    setBusy(true);
    try {
      const updated = await authApi.updateProfile({ display_name: clean });
      updateUser(updated);
      setName(updated.display_name);
      toast.success("تم حفظ الاسم.");
    } catch (err) {
      setError(err.fieldErrors?.display_name || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card settings-card">
      <h2 className="settings-title">الاسم الظاهر</h2>
      <form onSubmit={handleSubmit} noValidate className="settings-form">
        <TextField
          label="الاسم الذي يراه المتعاونون"
          value={name}
          maxLength={60}
          onChange={(e) => {
            setName(e.target.value);
            setError("");
          }}
          error={error}
          hint="يظهر الاسم الجديد للآخرين عند فتح المستند التالي."
        />
        <div>
          <Button type="submit" loading={busy} disabled={unchanged}>
            حفظ الاسم
          </Button>
        </div>
      </form>
    </section>
  );
}

const EMPTY_PASSWORDS = { current_password: "", new_password: "", new_password_confirm: "" };

function PasswordForm() {
  const toast = useToast();
  const [values, setValues] = useState(EMPTY_PASSWORDS);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const field = (name) => ({
    value: values[name],
    error: errors[name],
    onChange: (e) => {
      setValues((v) => ({ ...v, [name]: e.target.value }));
      setErrors((err) => ({ ...err, [name]: "", general: "" }));
    },
  });

  async function handleSubmit(event) {
    event.preventDefault();
    const missing = {};
    for (const [name, value] of Object.entries(values)) if (!value) missing[name] = "هذا الحقل مطلوب.";
    if (Object.keys(missing).length) return setErrors(missing);
    if (values.new_password !== values.new_password_confirm) {
      return setErrors({ new_password_confirm: "كلمتا المرور غير متطابقتين." });
    }
    setBusy(true);
    try {
      await authApi.changePassword(values);
      setValues(EMPTY_PASSWORDS);
      toast.success("تم تغيير كلمة المرور.");
    } catch (err) {
      const fieldErrors = err.fieldErrors || {};
      setErrors(Object.keys(fieldErrors).length ? fieldErrors : { general: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card settings-card">
      <h2 className="settings-title">كلمة المرور</h2>
      <form onSubmit={handleSubmit} noValidate className="settings-form">
        <TextField label="كلمة المرور الحالية" type="password" autoComplete="current-password" {...field("current_password")} />
        <TextField
          label="كلمة المرور الجديدة"
          type="password"
          autoComplete="new-password"
          hint="8 أحرف على الأقل، وليست شائعة أو أرقامًا فقط."
          {...field("new_password")}
        />
        <TextField label="تأكيد كلمة المرور الجديدة" type="password" autoComplete="new-password" {...field("new_password_confirm")} />
        {errors.general && <p className="field-error">{errors.general}</p>}
        <div>
          <Button type="submit" loading={busy}>
            تغيير كلمة المرور
          </Button>
        </div>
      </form>
    </section>
  );
}

export default function SettingsPage() {
  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">الإعدادات</h1>
          <p className="muted">عدّل اسمك الظاهر وكلمة المرور.</p>
        </div>
      </header>
      <ProfileForm />
      <PasswordForm />
    </div>
  );
}
