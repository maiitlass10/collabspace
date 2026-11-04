from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import DEFAULT_TITLE, Document

User = get_user_model()


class DocumentApiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email="alice@example.com", password="x", display_name="Alice")
        self.bob = User.objects.create_user(email="bob@example.com", password="x", display_name="Bob")
        self.client = APIClient()
        self.client.force_authenticate(self.alice)
        self.list_url = reverse("document-list")

    def detail_url(self, doc):
        return reverse("document-detail", args=[doc.id])

    # --- create -----------------------------------------------------------
    def test_create_with_title(self):
        response = self.client.post(self.list_url, {"title": "  خطة   المشروع  "}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "خطة المشروع")
        self.assertEqual(response.data["owner"]["display_name"], "Alice")
        self.assertEqual(Document.objects.get(id=response.data["id"]).owner, self.alice)

    def test_create_without_title_uses_default(self):
        response = self.client.post(self.list_url, {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], DEFAULT_TITLE)

    def test_create_with_too_long_title(self):
        response = self.client.post(self.list_url, {"title": "x" * 201}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.data)

    def test_owner_cannot_be_forged(self):
        response = self.client.post(self.list_url, {"title": "t", "owner": self.bob.id}, format="json")
        self.assertEqual(Document.objects.get(id=response.data["id"]).owner, self.alice)

    # --- list -------------------------------------------------------------
    def test_list_shows_only_my_documents(self):
        Document.objects.create(owner=self.alice, title="A1")
        Document.objects.create(owner=self.bob, title="B1")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d["title"] for d in response.data["results"]], ["A1"])

    def test_list_is_ordered_by_last_update(self):
        first = Document.objects.create(owner=self.alice, title="first")
        Document.objects.create(owner=self.alice, title="second")
        first.title = "first-renamed"
        first.save()
        titles = [d["title"] for d in self.client.get(self.list_url).data["results"]]
        self.assertEqual(titles, ["first-renamed", "second"])

    def test_search_by_title(self):
        Document.objects.create(owner=self.alice, title="تقرير المبيعات")
        Document.objects.create(owner=self.alice, title="خطة التسويق")
        response = self.client.get(self.list_url, {"search": "تقرير"})
        self.assertEqual([d["title"] for d in response.data["results"]], ["تقرير المبيعات"])

    def test_pagination(self):
        for i in range(15):
            Document.objects.create(owner=self.alice, title=f"doc {i}")
        page1 = self.client.get(self.list_url).data
        self.assertEqual(page1["count"], 15)
        self.assertEqual(len(page1["results"]), 12)
        self.assertIsNotNone(page1["next"])
        page2 = self.client.get(self.list_url, {"page": 2}).data
        self.assertEqual(len(page2["results"]), 3)

    # --- retrieve / rename / delete ----------------------------------------
    def test_retrieve_my_document(self):
        doc = Document.objects.create(owner=self.alice, title="mine")
        response = self.client.get(self.detail_url(doc))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(doc.id))

    def test_rename(self):
        doc = Document.objects.create(owner=self.alice, title="old")
        response = self.client.patch(self.detail_url(doc), {"title": "new"}, format="json")
        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.title, "new")

    def test_rename_to_blank_is_rejected(self):
        doc = Document.objects.create(owner=self.alice, title="old")
        response = self.client.patch(self.detail_url(doc), {"title": "   "}, format="json")
        self.assertEqual(response.status_code, 400)
        doc.refresh_from_db()
        self.assertEqual(doc.title, "old")

    def test_put_is_not_allowed(self):
        doc = Document.objects.create(owner=self.alice, title="old")
        response = self.client.put(self.detail_url(doc), {"title": "new"}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_delete(self):
        doc = Document.objects.create(owner=self.alice, title="bye")
        response = self.client.delete(self.detail_url(doc))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Document.objects.filter(id=doc.id).exists())

    # --- security: other users' documents ----------------------------------
    def test_cannot_read_rename_or_delete_someone_elses_document(self):
        bobs = Document.objects.create(owner=self.bob, title="secret")
        url = self.detail_url(bobs)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"title": "hacked"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        bobs.refresh_from_db()
        self.assertEqual(bobs.title, "secret")

    def test_unknown_or_invalid_id_returns_404(self):
        self.assertEqual(self.client.get("/api/documents/not-a-uuid/").status_code, 404)
        self.assertEqual(
            self.client.get("/api/documents/00000000-0000-0000-0000-000000000000/").status_code, 404
        )

    def test_anonymous_user_is_rejected(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get(self.list_url).status_code, 403)
        self.assertEqual(anonymous.post(self.list_url, {}, format="json").status_code, 403)

    def test_deleting_a_user_deletes_their_documents(self):
        Document.objects.create(owner=self.bob, title="b")
        self.bob.delete()
        self.assertFalse(Document.objects.filter(title="b").exists())


class DocumentCsrfTests(TestCase):
    """Writes from a real browser session must carry the CSRF token."""

    def test_create_without_csrf_token_is_rejected(self):
        User.objects.create_user(email="c@example.com", password="Collab#Space2026", display_name="C")
        client = APIClient(enforce_csrf_checks=True)
        client.login(email="c@example.com", password="Collab#Space2026")
        response = client.post(reverse("document-list"), {"title": "x"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Document.objects.exists())
