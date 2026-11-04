/**
 * Client-side validation gives instant feedback.
 * The server validates everything again: never trust the browser alone.
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLogin({ email, password }) {
  const errors = {};
  if (!email.trim()) errors.email = "أدخل البريد الإلكتروني.";
  else if (!EMAIL_RE.test(email.trim())) errors.email = "صيغة البريد الإلكتروني غير صحيحة.";
  if (!password) errors.password = "أدخل كلمة المرور.";
  return errors;
}

export function validateRegister({ display_name, email, password, password_confirm }) {
  const errors = {};
  const name = display_name.trim();
  if (!name) errors.display_name = "أدخل اسمك.";
  else if (name.length < 2) errors.display_name = "الاسم قصير جدًا.";
  else if (name.length > 60) errors.display_name = "الاسم طويل جدًا (60 حرفًا كحد أقصى).";

  if (!email.trim()) errors.email = "أدخل البريد الإلكتروني.";
  else if (!EMAIL_RE.test(email.trim())) errors.email = "صيغة البريد الإلكتروني غير صحيحة.";

  if (!password) errors.password = "أدخل كلمة المرور.";
  else if (password.length < 8) errors.password = "كلمة المرور يجب أن تكون 8 أحرف على الأقل.";
  else if (/^\d+$/.test(password)) errors.password = "كلمة المرور لا يمكن أن تكون أرقامًا فقط.";

  if (!password_confirm) errors.password_confirm = "أعد كتابة كلمة المرور.";
  else if (password !== password_confirm) errors.password_confirm = "كلمتا المرور غير متطابقتين.";

  return errors;
}
