from rest_framework.permissions import SAFE_METHODS, BasePermission

from .access import can_edit, can_manage, role_for


class DocumentRolePermission(BasePermission):
    """
    Object-level check based on the user's role (see access.py):
        read   -> any role (owner, editor, viewer)
        rename -> owner, editor
        delete -> owner only

    Documents the user cannot access at all never reach this check: they are
    not in the queryset, so the API answers 404.
    """

    def has_object_permission(self, request, view, obj):
        role = role_for(request.user, obj)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return can_manage(role)
        return can_edit(role)


class IsDocumentManager(BasePermission):
    """Only the owner may see and manage who a document is shared with."""

    message = "فقط مالك المستند يمكنه إدارة المشاركة."

    def has_object_permission(self, request, view, obj):
        return can_manage(role_for(request.user, obj))
