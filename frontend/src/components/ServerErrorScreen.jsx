import { useAuth } from "../context/AuthContext.jsx";
import Button from "./ui/Button.jsx";

export default function ServerErrorScreen() {
  const { refresh } = useAuth();
  return (
    <div className="full-page-center">
      <div className="card card-narrow text-center">
        <h1 className="card-title">تعذّر الاتصال بالخادم</h1>
        <p className="muted">تأكد من أن خادم Django يعمل، ثم أعد المحاولة.</p>
        <Button onClick={refresh}>إعادة المحاولة</Button>
      </div>
    </div>
  );
}
