import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <div className="full-page-center">
      <div className="card card-narrow text-center">
        <p className="big-code">404</p>
        <h1 className="card-title">الصفحة غير موجودة</h1>
        <p className="muted">ربما تم نقل الصفحة أو أن الرابط غير صحيح.</p>
        <Link to="/" className="btn btn-primary">
          العودة إلى الرئيسية
        </Link>
      </div>
    </div>
  );
}
