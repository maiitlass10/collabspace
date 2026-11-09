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


# =============================================================================
# Sprint 5: sharing and roles
# =============================================================================
from django.core.cache import cache  # noqa: E402

from .access import ROLE_EDITOR, ROLE_OWNER, ROLE_VIEWER, get_document_and_role  # noqa: E402
from .models import DocumentAccess  # noqa: E402


class SharingTestBase(TestCase):
    def setUp(self):
        cache.clear()  # reset the "share" throttle
        self.alice = User.objects.create_user(email="alice@example.com", password="x", display_name="Alice")
        self.bob = User.objects.create_user(email="bob@example.com", password="x", display_name="Bob")
        self.carol = User.objects.create_user(email="carol@example.com", password="x", display_name="Carol")
        self.doc = Document.objects.create(owner=self.alice, title="خطة")
        self.client = APIClient()
        self.as_user(self.alice)

    def as_user(self, user):
        self.client.force_authenticate(user)

    def share(self, user, role):
        return DocumentAccess.objects.create(document=self.doc, user=user, role=role, invited_by=self.alice)

    def detail_url(self, doc=None):
        return reverse("document-detail", args=[(doc or self.doc).id])

    def members_url(self, doc=None):
        return reverse("document-members", args=[(doc or self.doc).id])

    def member_url(self, access):
        return reverse("document-member-detail", args=[access.document_id, access.pk])


class RoleTests(SharingTestBase):
    def test_roles(self):
        self.share(self.bob, ROLE_VIEWER)
        self.assertEqual(get_document_and_role(self.alice, self.doc.id)[1], ROLE_OWNER)
        self.assertEqual(get_document_and_role(self.bob, self.doc.id)[1], ROLE_VIEWER)
        self.assertEqual(get_document_and_role(self.carol, self.doc.id), (None, None))

    def test_one_access_per_user_and_document(self):
        from django.db import IntegrityError

        self.share(self.bob, ROLE_VIEWER)
        with self.assertRaises(IntegrityError):
            self.share(self.bob, ROLE_EDITOR)


class SharedDocumentApiTests(SharingTestBase):
    def test_shared_document_appears_in_lists_with_role(self):
        self.share(self.bob, ROLE_EDITOR)
        Document.objects.create(owner=self.bob, title="لبوب")
        self.as_user(self.bob)

        everything = self.client.get(reverse("document-list")).json()
        self.assertEqual(everything["count"], 2)

        shared = self.client.get(reverse("document-list"), {"scope": "shared"}).json()
        self.assertEqual([d["title"] for d in shared["results"]], ["خطة"])
        self.assertEqual(shared["results"][0]["role"], ROLE_EDITOR)
        self.assertEqual(shared["results"][0]["owner"]["display_name"], "Alice")

        owned = self.client.get(reverse("document-list"), {"scope": "owned"}).json()
        self.assertEqual([d["title"] for d in owned["results"]], ["لبوب"])
        self.assertEqual(owned["results"][0]["role"], ROLE_OWNER)

    def test_no_duplicates_when_owner_shared_with_many(self):
        self.share(self.bob, ROLE_VIEWER)
        self.share(self.carol, ROLE_VIEWER)
        self.assertEqual(self.client.get(reverse("document-list")).json()["count"], 1)

    def test_viewer_can_read_but_not_rename_or_delete(self):
        self.share(self.bob, ROLE_VIEWER)
        self.as_user(self.bob)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], ROLE_VIEWER)
        self.assertEqual(self.client.patch(self.detail_url(), {"title": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.detail_url()).status_code, 403)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, "خطة")

    def test_editor_can_rename_but_not_delete(self):
        self.share(self.bob, ROLE_EDITOR)
        self.as_user(self.bob)
        self.assertEqual(self.client.patch(self.detail_url(), {"title": "جديد"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.detail_url()).status_code, 403)
        self.assertTrue(Document.objects.filter(pk=self.doc.pk).exists())

    def test_stranger_still_gets_404(self):
        self.as_user(self.carol)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404)
        self.assertEqual(self.client.get(self.members_url()).status_code, 404)


class MembersApiTests(SharingTestBase):
    def test_owner_shares_by_email(self):
        response = self.client.post(self.members_url(), {"email": " BOB@Example.com ", "role": "editor"}, format="json")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["user"]["display_name"], "Bob")
        self.assertEqual(body["role"], "editor")
        self.assertRegex(body["user"]["color"], r"^#[0-9a-f]{6}$")
        access = DocumentAccess.objects.get(document=self.doc, user=self.bob)
        self.assertEqual(access.invited_by, self.alice)

    def test_list_members(self):
        self.share(self.bob, ROLE_VIEWER)
        body = self.client.get(self.members_url()).json()
        self.assertEqual(body["owner"]["display_name"], "Alice")
        self.assertEqual([(m["user"]["email"], m["role"]) for m in body["members"]], [("bob@example.com", "viewer")])

    def test_share_errors(self):
        cases = [
            ({"email": "nobody@example.com", "role": "viewer"}, "email"),
            ({"email": "alice@example.com", "role": "viewer"}, "email"),
            ({"email": "not-an-email", "role": "viewer"}, "email"),
            ({"email": "bob@example.com", "role": "owner"}, "role"),
            ({"email": "bob@example.com"}, "role"),
        ]
        for data, field in cases:
            with self.subTest(data=data):
                response = self.client.post(self.members_url(), data, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertFalse(DocumentAccess.objects.exists())

    def test_cannot_share_twice(self):
        self.share(self.bob, ROLE_VIEWER)
        response = self.client.post(self.members_url(), {"email": "bob@example.com", "role": "editor"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_inactive_user_cannot_be_invited(self):
        self.bob.is_active = False
        self.bob.save()
        response = self.client.post(self.members_url(), {"email": "bob@example.com", "role": "viewer"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_only_owner_manages_sharing(self):
        bob_access = self.share(self.bob, ROLE_EDITOR)
        carol_access = self.share(self.carol, ROLE_VIEWER)
        self.as_user(self.bob)  # an editor, not the owner
        self.assertEqual(self.client.get(self.members_url()).status_code, 403)
        response = self.client.post(self.members_url(), {"email": "x@example.com", "role": "viewer"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.patch(self.member_url(bob_access), {"role": "editor"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.member_url(carol_access)).status_code, 403)
        self.assertEqual(DocumentAccess.objects.count(), 2)

    def test_owner_changes_role_and_removes_member(self):
        access = self.share(self.bob, ROLE_VIEWER)
        response = self.client.patch(self.member_url(access), {"role": "editor"}, format="json")
        self.assertEqual(response.status_code, 200)
        access.refresh_from_db()
        self.assertEqual(access.role, ROLE_EDITOR)

        self.assertEqual(self.client.delete(self.member_url(access)).status_code, 204)
        self.as_user(self.bob)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404, "access is really gone")

    def test_member_can_leave(self):
        access = self.share(self.bob, ROLE_VIEWER)
        self.as_user(self.bob)
        self.assertEqual(self.client.delete(self.member_url(access)).status_code, 204)
        self.assertFalse(DocumentAccess.objects.exists())

    def test_member_of_another_document_is_404(self):
        other = Document.objects.create(owner=self.alice, title="آخر")
        access = DocumentAccess.objects.create(document=other, user=self.bob, role=ROLE_VIEWER)
        url = reverse("document-member-detail", args=[self.doc.id, access.pk])  # wrong document
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(DocumentAccess.objects.filter(pk=access.pk).exists())

    def test_deleting_document_deletes_accesses(self):
        self.share(self.bob, ROLE_VIEWER)
        self.assertEqual(self.client.delete(self.detail_url()).status_code, 204)
        self.assertFalse(DocumentAccess.objects.exists())

    def test_inviting_is_rate_limited(self):
        from rest_framework.settings import api_settings

        limit = int(api_settings.DEFAULT_THROTTLE_RATES["share"].split("/")[0])
        for _ in range(limit):
            self.client.post(self.members_url(), {"email": "nobody@example.com", "role": "viewer"}, format="json")
        response = self.client.post(self.members_url(), {"email": "bob@example.com", "role": "viewer"}, format="json")
        self.assertEqual(response.status_code, 429)


# =============================================================================
# Sprint 6: activity log and versions
# =============================================================================
import base64  # noqa: E402

from pycrdt import Doc, Text  # noqa: E402

from .activity import log_edit  # noqa: E402
from .models import ActivityLog, DocumentVersion  # noqa: E402


def yjs_state_with(text):
    doc = Doc()
    doc["content"] = t = Text()
    t += text
    return doc.get_update()


def text_in(state):
    doc = Doc()
    doc.apply_update(state)
    doc["content"] = t = Text()
    return str(t)


class ActivityTests(SharingTestBase):
    def actions(self):
        return list(ActivityLog.objects.filter(document=self.doc).order_by("created_at", "id").values_list("action", flat=True))

    def test_create_and_rename_are_logged(self):
        response = self.client.post(reverse("document-list"), {"title": "جديد"}, format="json")
        doc = Document.objects.get(pk=response.json()["id"])
        self.client.patch(self.detail_url(doc), {"title": "اسم آخر"}, format="json")
        self.client.patch(self.detail_url(doc), {"title": "اسم آخر"}, format="json")  # no change: not logged
        logs = list(ActivityLog.objects.filter(document=doc).order_by("created_at", "id"))
        self.assertEqual([log.action for log in logs], ["created", "renamed"])
        self.assertEqual(logs[1].metadata, {"from": "جديد", "to": "اسم آخر"})
        self.assertEqual(logs[1].actor, self.alice)

    def test_sharing_actions_are_logged(self):
        self.client.post(self.members_url(), {"email": "bob@example.com", "role": "viewer"}, format="json")
        bob = DocumentAccess.objects.get(user=self.bob)
        self.client.patch(self.member_url(bob), {"role": "editor"}, format="json")
        self.client.delete(self.member_url(bob))
        carol = self.share(self.carol, ROLE_VIEWER)
        self.as_user(self.carol)
        self.client.delete(self.member_url(carol))  # Carol leaves

        self.assertEqual(self.actions(), ["shared", "role_changed", "unshared", "left"])
        role_change = ActivityLog.objects.get(action="role_changed")
        self.assertEqual(role_change.metadata["target"], {"id": self.bob.pk, "display_name": "Bob"})
        self.assertEqual((role_change.metadata["from"], role_change.metadata["to"]), ("viewer", "editor"))

    def test_activity_endpoint(self):
        ActivityLog.objects.create(document=self.doc, actor=self.alice, action="created")
        ActivityLog.objects.create(document=self.doc, actor=self.alice, action="renamed", metadata={"from": "a", "to": "b"})
        self.share(self.bob, ROLE_VIEWER)
        self.as_user(self.bob)  # viewers can read the history too
        body = self.client.get(reverse("document-activity", args=[self.doc.id])).json()
        self.assertEqual([item["action"] for item in body["results"]], ["renamed", "created"], "newest first")
        self.assertEqual(body["results"][0]["actor"]["display_name"], "Alice")
        self.assertNotIn("email", body["results"][0]["actor"])

        self.as_user(self.carol)
        self.assertEqual(self.client.get(reverse("document-activity", args=[self.doc.id])).status_code, 404)

    def test_history_survives_when_actor_is_deleted(self):
        ActivityLog.objects.create(document=self.doc, actor=self.bob, action="edited")
        self.bob.delete()
        body = self.client.get(reverse("document-activity", args=[self.doc.id])).json()
        self.assertIsNone(body["results"][0]["actor"])

    def test_consecutive_edits_are_merged(self):
        log_edit(self.doc.id, self.bob)
        log_edit(self.doc.id, self.bob)
        self.assertEqual(ActivityLog.objects.filter(action="edited").count(), 1)
        log_edit(self.doc.id, self.carol)  # someone else: a new entry
        log_edit(self.doc.id, self.bob)  # Bob again after Carol: a new entry
        self.assertEqual(ActivityLog.objects.filter(action="edited").count(), 3)


class VersionTests(SharingTestBase):
    def setUp(self):
        super().setUp()
        self.doc.yjs_state = yjs_state_with("النسخة الأولى")
        self.doc.save()

    def versions_url(self):
        return reverse("document-versions", args=[self.doc.id])

    def version_url(self, version, suffix=""):
        name = "document-version-restore" if suffix == "restore" else "document-version-detail"
        return reverse(name, args=[self.doc.id, version.pk])

    def test_save_list_and_preview_a_version(self):
        response = self.client.post(self.versions_url(), {"label": "  مسودة   أولى "}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["label"], "مسودة أولى")
        self.assertEqual(response.json()["created_by"]["display_name"], "Alice")
        version = DocumentVersion.objects.get()

        listed = self.client.get(self.versions_url()).json()
        self.assertEqual(len(listed), 1)
        self.assertNotIn("state", listed[0], "the list stays small")

        detail = self.client.get(self.version_url(version)).json()
        self.assertEqual(text_in(base64.b64decode(detail["state"])), "النسخة الأولى")
        self.assertEqual(ActivityLog.objects.get().action, "version_saved")

    def test_empty_document_cannot_be_saved(self):
        empty = Document.objects.create(owner=self.alice, title="فارغ")
        response = self.client.post(reverse("document-versions", args=[empty.id]), {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_label_too_long(self):
        response = self.client.post(self.versions_url(), {"label": "x" * 101}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_restore_saves_a_backup_first(self):
        version = DocumentVersion.objects.create(
            document=self.doc, created_by=self.alice, label="قديم", yjs_state=yjs_state_with("نص قديم")
        )
        response = self.client.post(self.version_url(version, "restore"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(text_in(base64.b64decode(body["version"]["state"])), "نص قديم")
        backup = DocumentVersion.objects.get(pk=body["backup"]["id"])
        self.assertEqual(backup.kind, DocumentVersion.KIND_BACKUP)
        self.assertEqual(text_in(bytes(backup.yjs_state)), "النسخة الأولى", "the current content is kept")
        self.assertEqual(ActivityLog.objects.get().action, "version_restored")

    def test_viewer_can_preview_but_not_save_or_restore(self):
        version = DocumentVersion.objects.create(document=self.doc, yjs_state=yjs_state_with("x"))
        self.share(self.bob, ROLE_VIEWER)
        self.as_user(self.bob)
        self.assertEqual(self.client.get(self.versions_url()).status_code, 200)
        self.assertEqual(self.client.get(self.version_url(version)).status_code, 200)
        self.assertEqual(self.client.post(self.versions_url(), {}, format="json").status_code, 403)
        self.assertEqual(self.client.post(self.version_url(version, "restore")).status_code, 403)
        self.assertEqual(DocumentVersion.objects.count(), 1)

    def test_editor_can_save_and_restore(self):
        version = DocumentVersion.objects.create(document=self.doc, yjs_state=yjs_state_with("x"))
        self.share(self.bob, ROLE_EDITOR)
        self.as_user(self.bob)
        self.assertEqual(self.client.post(self.versions_url(), {}, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.version_url(version, "restore")).status_code, 200)

    def test_versions_of_other_documents_are_hidden(self):
        other = Document.objects.create(owner=self.bob, title="لبوب", yjs_state=yjs_state_with("سر"))
        secret = DocumentVersion.objects.create(document=other, yjs_state=yjs_state_with("سر"))
        # Through Alice's own document id: 404.
        self.assertEqual(self.client.get(self.version_url(secret)).status_code, 404)
        # Directly: 404 as well.
        url = reverse("document-version-detail", args=[other.id, secret.pk])
        self.assertEqual(self.client.get(url).status_code, 404)


class SnapshotRequestValidationTests(SharingTestBase):
    def test_invalid_browser_state_is_rejected(self):
        self.doc.yjs_state = yjs_state_with("x")
        self.doc.save()
        url = reverse("document-versions", args=[self.doc.id])
        for bad in ["%%%", base64.b64encode(b"not yjs at all").decode()]:
            with self.subTest(bad=bad):
                self.assertEqual(self.client.post(url, {"browser_state": bad}, format="json").status_code, 400)
        ok = base64.b64encode(yjs_state_with("x")).decode()
        self.assertEqual(self.client.post(url, {"browser_state": ok}, format="json").status_code, 201)
