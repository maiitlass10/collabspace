from rest_framework.permissions import BasePermission


class IsDocumentOwner(BasePermission):
    """
    Object-level check: only the owner may read or change a document.

    Sprint 5 will extend this with shared access (viewer / editor roles).
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
