# CollabSpace – Real-Time Collaborative Editor

منصة ويب لتحرير المستندات بشكل تعاوني ولحظي.
Django + Channels (الخادم) و React + Vite (الواجهة) و Yjs (المزامنة).

> الحالة الحالية: **سبرينت 3 – المحرر التعاوني اللحظي**

## المتطلبات
- Python 3.11 أو أحدث
- Node.js 20.19+ أو 22.12+ (شرط Vite 8)
- Git

## التشغيل

### 1) الخادم (الطرفية الأولى)
```bash
cd backend
# Windows (PowerShell):  py -m venv .venv   ثم   .\.venv\Scripts\Activate.ps1
# macOS/Linux:           python3 -m venv .venv   ثم   source .venv/bin/activate
pip install --only-binary=:all: -r requirements.txt
# Windows: copy .env.example .env   |   macOS/Linux: cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"   # ضع الناتج في DJANGO_SECRET_KEY داخل .env
python manage.py migrate
python manage.py runserver
```

### 2) الواجهة (الطرفية الثانية)
```bash
cd frontend
npm install
npm run dev
```

ثم افتح http://localhost:5173

## الاختبارات
```bash
cd backend
python manage.py test
```

## PostgreSQL (اختياري)
```bash
docker compose up -d
```
ثم فعّل سطر `DATABASE_URL=postgres://...` في `backend/.env`.

## واجهات API الحالية

| Method | Endpoint | الوصف | يتطلب دخول |
|---|---|---|---|
| GET | `/api/health/` | فحص الخادم وقاعدة البيانات | لا |
| GET | `/api/auth/session/` | من المستخدم الحالي؟ + يضع كوكي CSRF | لا |
| POST | `/api/auth/register/` | `{email, display_name, password, password_confirm}` ← ينشئ الحساب ويسجّل الدخول | لا (CSRF مطلوب) |
| POST | `/api/auth/login/` | `{email, password}` ← يبدأ جلسة | لا (CSRF مطلوب) |
| POST | `/api/auth/logout/` | ينهي الجلسة | نعم |
| GET | `/api/documents/?search=&page=` | قائمة مستنداتي (12 في الصفحة، الأحدث أولًا) | نعم |
| POST | `/api/documents/` | `{title?}` ← إنشاء مستند (عنوان افتراضي إن كان فارغًا) | نعم |
| GET | `/api/documents/<uuid>/` | تفاصيل مستند | نعم (المالك فقط) |
| PATCH | `/api/documents/<uuid>/` | `{title}` ← إعادة تسمية | نعم (المالك فقط) |
| DELETE | `/api/documents/<uuid>/` | حذف | نعم (المالك فقط) |

مستندات المستخدمين الآخرين تُرجع **404** (لا نكشف حتى وجودها).

كل طلبات POST يجب أن تحمل الترويسة `X-CSRFToken` بقيمة الكوكي `csrftoken`.

## التعاون اللحظي (WebSocket)

`ws://<host>/ws/documents/<uuid>` — بروتوكول Yjs الثنائي (متوافق مع `y-websocket`).

- الهوية من كوكي الجلسة، والصلاحية تُفحص في الخادم قبل إرسال أي بيانات.
- رموز الإغلاق: `4401` غير مسجّل الدخول، `4403` لا صلاحية / غير موجود، `4413` رسالة أكبر من 5MB.
- الخادم يحتفظ بنسخة `pycrdt.Doc` لكل مستند مفتوح، ويحفظها في `Document.yjs_state` بعد ثانيتين من آخر تعديل وفورًا عند خروج آخر مستخدم.
- ملاحظة: الغرف في ذاكرة عملية واحدة؛ التشغيل بعدة عمليات يحتاج مخزنًا مشتركًا (سيُوثّق في دليل النشر).

## البنية
```
backend/   Django + DRF + Channels  (config/ الإعدادات، core/ الفحص، accounts/ المستخدمون والمصادقة، documents/ المستندات، collaboration/ التحرير اللحظي)
frontend/  React + Vite (RTL)
```
