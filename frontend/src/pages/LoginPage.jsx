import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";
import Alert from "../components/ui/Alert.jsx";
import Button from "../components/ui/Button.jsx";
import TextField from "../components/ui/TextField.jsx";
import { validateLogin } from "../utils/validation.js";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const justRegistered = location.state?.registered;

  function update(field) {
    return (event) => {
      setForm((f) => ({ ...f, [field]: event.target.value }));
      setErrors((e) => ({ ...e, [field]: undefined }));
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    const clientErrors = validateLogin(form);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    setSubmitting(true);
    try {
      await login(form.email.trim(), form.password);
      navigate(location.state?.from || "/", { replace: true });
    } catch (error) {
      setErrors(error.fieldErrors || {});
      setFormError(error.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-card">
      <h1 className="auth-title">تسجيل الدخول</h1>
      <p className="muted">مرحبًا بعودتك! أدخل بياناتك للمتابعة.</p>

      {justRegistered && <Alert type="success">تم إنشاء حسابك بنجاح.</Alert>}
      <Alert type="error">{formError}</Alert>

      <form onSubmit={handleSubmit} noValidate className="form">
        <TextField
          label="البريد الإلكتروني"
          type="email"
          autoComplete="email"
          dir="ltr"
          value={form.email}
          onChange={update("email")}
          error={errors.email}
          autoFocus
        />
        <TextField
          label="كلمة المرور"
          type="password"
          autoComplete="current-password"
          dir="ltr"
          value={form.password}
          onChange={update("password")}
          error={errors.password}
        />
        <Button type="submit" block loading={submitting}>
          {submitting ? "جارٍ تسجيل الدخول…" : "تسجيل الدخول"}
        </Button>
      </form>

      <p className="auth-switch">
        ليس لديك حساب؟ <Link to="/register">أنشئ حسابًا جديدًا</Link>
      </p>
    </div>
  );
}
