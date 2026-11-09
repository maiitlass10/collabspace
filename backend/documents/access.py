"""
Single place that answers: "what may this user do with this document?"

Both the REST API and the WebSocket consumer use it, so permissions can never
drift apart between the two.

Roles:
    owner  - everything: edit, rename, share, delete
    editor - edit content and rename
    viewer - read only
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import OuterRef, Q, Subquery

from .models import Document, DocumentAccess

ROLE_OWNER = "owner"
ROLE_EDITOR = DocumentAccess.ROLE_EDITOR
ROLE_VIEWER = DocumentAccess.ROLE_VIEWER


def accessible_documents(user):
    """
    Every document the user may open, annotated with `shared_role`
    (None for documents the user owns).
    """
    shared_ids = DocumentAccess.objects.filter(user=user).values("document_id")
    shared_role = DocumentAccess.objects.filter(document=OuterRef("pk"), user=user).values("role")[:1]
    return (
        Document.objects.filter(Q(owner=user) | Q(pk__in=shared_ids))
        .annotate(shared_role=Subquery(shared_role))
        .select_related("owner")
    )


def role_for(user, document):
    """The user's role on `document`, or None if they have no access."""
    if not user or not user.is_authenticated:
        return None
    if document.owner_id == user.id:
        return ROLE_OWNER
    if hasattr(document, "shared_role"):  # already annotated by accessible_documents()
        return document.shared_role
    return DocumentAccess.objects.filter(document=document, user=user).values_list("role", flat=True).first()


def get_document_and_role(user, document_id):
    """Return (document, role) or (None, None) if missing or not accessible."""
    if not user or not user.is_authenticated:
        return None, None
    try:
        document = Document.objects.get(pk=document_id)
    except (Document.DoesNotExist, ValueError):
        return None, None
    role = role_for(user, document)
    return (document, role) if role else (None, None)


def can_edit(role):
    return role in (ROLE_OWNER, ROLE_EDITOR)


def can_manage(role):
    """Share, change roles, delete."""
    return role == ROLE_OWNER


def notify_access_changed(document_id, user_id=None):
    """
    Tell open editors that permissions changed, so they reconnect and get
    their NEW role checked (or are refused if access was removed).
    user_id=None means "everyone in this document" (e.g. it was deleted).
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"document_{document_id}",
        {"type": "access.changed", "user_id": user_id},
    )
