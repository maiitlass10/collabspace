import uuid

from django.conf import settings
from django.db import models

DEFAULT_TITLE = "مستند بلا عنوان"
TITLE_MAX_LENGTH = 200


class Document(models.Model):
    """
    A collaborative document.

    The id is a random UUID (not 1, 2, 3...) so document URLs cannot be guessed.
    The content itself is stored in `yjs_state` (binary Yjs update) starting in
    Sprint 3; it is empty until the document is first edited.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="المالك",
    )
    title = models.CharField("العنوان", max_length=TITLE_MAX_LENGTH, default=DEFAULT_TITLE)
    yjs_state = models.BinaryField("حالة Yjs", null=True, blank=True, editable=False)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("آخر تعديل", auto_now=True)

    class Meta:
        verbose_name = "مستند"
        verbose_name_plural = "المستندات"
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["owner", "-updated_at"], name="doc_owner_updated_idx")]

    def __str__(self):
        return self.title
