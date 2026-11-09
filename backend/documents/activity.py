"""Writing to the activity log (documents.ActivityLog) from one place."""
from datetime import timedelta

from django.utils import timezone

from .models import ActivityLog

# Typing for an hour should not create hundreds of "edited" rows:
# consecutive edits by the same person within this window are merged.
EDIT_MERGE_WINDOW = timedelta(minutes=10)


def person(user):
    """How a user is stored inside metadata (kept even if they are deleted later)."""
    return {"id": user.pk, "display_name": user.display_name}


def log_activity(document, actor, action, **metadata):
    return ActivityLog.objects.create(document=document, actor=actor, action=action, metadata=metadata)


def log_edit(document_id, actor):
    """Record that `actor` edited the content (merged within EDIT_MERGE_WINDOW)."""
    now = timezone.now()
    recent = (
        ActivityLog.objects.filter(document_id=document_id, created_at__gte=now - EDIT_MERGE_WINDOW)
        .order_by("-created_at", "-id")
        .first()
    )
    if recent and recent.action == ActivityLog.EDITED and recent.actor_id == actor.pk:
        ActivityLog.objects.filter(pk=recent.pk).update(created_at=now)
        return recent
    return ActivityLog.objects.create(document_id=document_id, actor=actor, action=ActivityLog.EDITED)
