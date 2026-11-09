from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

STRONG_PASSWORD = "Collab#Space2026"


class AuthTestMixin:
    def setUp(self):
        cache.clear()  # reset throttling counters between tests
        # enforce_csrf_checks=True makes the test client behave like a real browser.
        self.client = APIClient(enforce_csrf_checks=True)

    def get_csrf(self):
        response = self.client.get(reverse("auth-session"))
        return response.cookies["csrftoken"].value

    def post(self, name, data=None):
        token = self.get_csrf()
        return self.client.post(reverse(name), data or {}, format="json", HTTP_X_CSRFTOKEN=token)

    def register(self, **overrides):
        data = {
            "email": "sara@example.com",
            "display_name": "سارة",
            "password": STRONG_PASSWORD,
            "password_confirm": STRONG_PASSWORD,
        }
        data.update(overrides)
        return self.post("auth-register", data)


class UserModelTests(TestCase):
    def test_email_is_normalised_to_lowercase(self):
        user = User.objects.create_user(email="Ali@Example.COM", password="x", display_name="علي")
        self.assertEqual(user.email, "ali@example.com")

    def test_password_is_hashed(self):
        user = User.objects.create_user(email="a@b.com", password=STRONG_PASSWORD, display_name="A")
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@b.com", password="x", display_name="Admin")
        self.assertTrue(admin.is_staff and admin.is_superuser)


class SessionEndpointTests(AuthTestMixin, TestCase):
    def test_anonymous_session(self):
        response = self.client.get(reverse("auth-session"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})
        self.assertIn("csrftoken", response.cookies)


class RegisterTests(AuthTestMixin, TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["user"]["email"], "sara@example.com")
        self.assertNotIn("password", body["user"])
        # The session is active: /session/ now reports the user.
        self.assertTrue(self.client.get(reverse("auth-session")).json()["authenticated"])

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.register()
        self.client.post(reverse("auth-logout"), HTTP_X_CSRFTOKEN=self.get_csrf())
        response = self.register(email="SARA@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_password_mismatch(self):
        response = self.register(password_confirm="Different#2026")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.json())

    def test_weak_password_is_rejected(self):
        response = self.register(password="12345678", password_confirm="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())

    def test_invalid_email_and_missing_name(self):
        response = self.register(email="not-an-email", display_name="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertIn("display_name", response.json())

    def test_register_without_csrf_token_is_rejected(self):
        response = self.client.post(
            reverse("auth-register"),
            {"email": "x@y.com", "display_name": "X", "password": STRONG_PASSWORD,
             "password_confirm": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email="x@y.com").exists())


class LoginLogoutTests(AuthTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(email="omar@example.com", password=STRONG_PASSWORD, display_name="عمر")

    def test_login_success(self):
        response = self.post("auth-login", {"email": "omar@example.com", "password": STRONG_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertIn("sessionid", response.cookies)
        self.assertTrue(response.cookies["sessionid"]["httponly"])

    def test_session_includes_presence_color(self):
        self.post("auth-login", {"email": "omar@example.com", "password": STRONG_PASSWORD})
        user = self.client.get(reverse("auth-session")).json()["user"]
        self.assertRegex(user["color"], r"^#[0-9a-f]{6}$")
        self.assertEqual(user["display_name"], "عمر")

    def test_login_email_is_case_insensitive(self):
        response = self.post("auth-login", {"email": "OMAR@Example.com", "password": STRONG_PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_and_unknown_email_give_same_error(self):
        wrong = self.post("auth-login", {"email": "omar@example.com", "password": "nope"})
        unknown = self.post("auth-login", {"email": "ghost@example.com", "password": "nope"})
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.json(), unknown.json())

    def test_inactive_user_cannot_login(self):
        User.objects.filter(email="omar@example.com").update(is_active=False)
        response = self.post("auth-login", {"email": "omar@example.com", "password": STRONG_PASSWORD})
        self.assertEqual(response.status_code, 400)

    def test_logout_ends_session(self):
        self.post("auth-login", {"email": "omar@example.com", "password": STRONG_PASSWORD})
        response = self.post("auth-logout")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.client.get(reverse("auth-session")).json()["authenticated"])

    def test_logout_requires_authentication(self):
        response = self.post("auth-logout")
        self.assertEqual(response.status_code, 403)

    def test_login_is_throttled(self):
        statuses = [
            self.post("auth-login", {"email": "omar@example.com", "password": "bad"}).status_code
            for _ in range(11)
        ]
        self.assertEqual(statuses[:10], [400] * 10)
        self.assertEqual(statuses[10], 429)


class SettingsTests(AuthTestMixin, TestCase):
    """Sprint 6: change display name and password."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="omar@example.com", password=STRONG_PASSWORD, display_name="عمر")
        self.post("auth-login", {"email": "omar@example.com", "password": STRONG_PASSWORD})

    def patch(self, name, data):
        return self.client.patch(reverse(name), data, format="json", HTTP_X_CSRFTOKEN=self.get_csrf())

    def test_change_display_name(self):
        response = self.patch("auth-profile", {"display_name": "  عمر   خالد "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "عمر خالد")
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "عمر خالد")

    def test_invalid_display_name(self):
        for value in ["", "ع", "x" * 61]:
            with self.subTest(value=value):
                self.assertEqual(self.patch("auth-profile", {"display_name": value}).status_code, 400)

    def test_email_cannot_be_changed_through_profile(self):
        self.patch("auth-profile", {"email": "hacker@example.com", "display_name": "عمر"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "omar@example.com")

    def change_password(self, current, new, confirm=None):
        return self.post(
            "auth-password",
            {"current_password": current, "new_password": new, "new_password_confirm": confirm or new},
        )

    def test_change_password_keeps_this_session(self):
        new = "Brand#New2026pass"
        self.assertEqual(self.change_password(STRONG_PASSWORD, new).status_code, 204)
        self.assertTrue(self.client.get(reverse("auth-session")).json()["authenticated"], "still logged in")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))

    def test_change_password_errors(self):
        cases = [
            (("wrong-password", "Brand#New2026pass"), "current_password"),
            ((STRONG_PASSWORD, "Brand#New2026pass", "different"), "new_password_confirm"),
            ((STRONG_PASSWORD, "123"), "new_password"),
            ((STRONG_PASSWORD, STRONG_PASSWORD), "new_password"),
        ]
        for args, field in cases:
            with self.subTest(field=field, args=args):
                response = self.change_password(*args)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))

    def test_settings_require_login(self):
        self.post("auth-logout")
        self.assertEqual(self.patch("auth-profile", {"display_name": "x y"}).status_code, 403)
