import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";
import Alert from "../components/ui/Alert.jsx";
import Button from "../components/ui/Button.jsx";
import TextField from "../components/ui/TextField.jsx";
import { validateRegister } from "../utils/validation.js";

const EMPTY_FORM = { display_name: "", email: "", password: "", password_confirm: "" };

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (event) => {
      setForm((f) => ({ ...f, [field]: event.target.value }));
      setErrors((e) => ({ ...e, [field]: undefined }));
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    const clientErrors = validateRegister(form);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    setSubmitting(true);
    try {
      await register({ ...form, display_name: form.display_name.trim(), email: form.email.trim() });
      navigate("/", { replace: true, state: { welcome: true } });
    } catch (error) {
      setErrors(error.fieldErrors || {});
      // Field errors are shown under each input; show a general message too.
      setFormError(error.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-card">
      <h1 className="auth-title">إنشاء حساب جديد</h1>
      <p className="muted">ابدأ بكتابة مستنداتك ومشاركتها مع فريقك.</p>

      <Alert type="error">{formError}</Alert>

      <form onSubmit={handleSubmit} noValidate className="form">
        <TextField
          label="الاسم"
          autoComplete="name"
          value={form.display_name}
          onChange={update("display_name")}
          error={errors.display_name}
          hint="سيظهر هذا الاسم لزملائك أثناء التحرير."
          autoFocus
        />
        <TextField
          label="البريد الإلكتروني"
          type="email"
          autoComplete="email"
          dir="ltr"
          value={form.email}
          onChange={update("email")}
          error={errors.email}
        />
        <TextField
          label="كلمة المرور"
          type="password"
          autoComplete="new-password"
          dir="ltr"
          value={form.password}
          onChange={update("password")}
          error={errors.password}
          hint="8 أحرف على الأقل، ولا تكون أرقامًا فقط أو كلمة شائعة."
        />
        <TextField
          label="تأكيد كلمة المرور"
          type="password"
          autoComplete="new-password"
          dir="ltr"
          value={form.password_confirm}
          onChange={update("password_confirm")}
          error={errors.password_confirm}
        />
        <Button type="submit" block loading={submitting}>
          {submitting ? "جارٍ إنشاء الحساب…" : "إنشاء الحساب"}
        </Button>
      </form>

      <p className="auth-switch">
        لديك حساب بالفعل؟ <Link to="/login">سجّل الدخول</Link>
      </p>
    </div>
  );
}
