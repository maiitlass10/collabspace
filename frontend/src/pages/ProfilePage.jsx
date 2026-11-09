import { useAuth } from "../context/AuthContext.jsx";
import Avatar from "../components/ui/Avatar.jsx";

const dateFormatter = new Intl.DateTimeFormat("ar", { dateStyle: "long" });

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="page-container">
      <header className="page-header">
        <h1 className="page-title">الملف الشخصي</h1>
      </header>

      <section className="card profile-card">
        <Avatar name={user.display_name} color={user.color} size={72} />
        <div>
          <h2 className="profile-name">{user.display_name}</h2>
          <p className="muted">
            <bdi dir="ltr">{user.email}</bdi>
          </p>
        </div>
      </section>

      <section className="card">
        <dl className="details-list">
          <div>
            <dt>الاسم الظاهر</dt>
            <dd>{user.display_name}</dd>
          </div>
          <div>
            <dt>البريد الإلكتروني</dt>
            <dd>
              <bdi dir="ltr">{user.email}</bdi>
            </dd>
          </div>
          <div>
            <dt>تاريخ الانضمام</dt>
            <dd>{dateFormatter.format(new Date(user.date_joined))}</dd>
          </div>
        </dl>
        <p className="muted small">تعديل الاسم وكلمة المرور سيكون متاحًا في صفحة الإعدادات لاحقًا.</p>
      </section>
    </div>
  );
}
