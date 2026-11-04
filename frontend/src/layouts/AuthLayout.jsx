import { Outlet } from "react-router";

export default function AuthLayout() {
  return (
    <div className="auth-layout">
      <aside className="auth-hero" aria-hidden="true">
        <div className="brand brand--light">
          <span className="brand-logo">C</span>
          <span className="brand-name">CollabSpace</span>
        </div>
        <h2 className="auth-hero-title">اكتبوا معًا، في اللحظة نفسها.</h2>
        <p className="auth-hero-text">
          محرر مستندات تعاوني يتيح لفريقك العمل على المستند نفسه، ورؤية تعديلات الجميع مباشرةً.
        </p>
      </aside>
      <main className="auth-main">
        <Outlet />
      </main>
    </div>
  );
}
