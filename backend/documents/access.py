"""
Single place that answers: "what may this user do with this document?"

Both the REST API and the WebSocket consumer use it, so permissions can never
drift apart between the two. Sprint 5 adds shared roles (editor / viewer).
"""
from .models import Document

ROLE_OWNER = "owner"


def get_document_and_role(user, document_id):
    """Return (document, role) or (None, None) if missing or not accessible."""
    if not user or not user.is_authenticated:
        return None, None
    try:
        document = Document.objects.get(pk=document_id)
    except (Document.DoesNotExist, ValueError):
        return None, None
    if document.owner_id == user.id:
        return document, ROLE_OWNER
    return None, None


def can_edit(role):
    return role == ROLE_OWNER
