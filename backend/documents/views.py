from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from collaboration.rooms import flush_open_document

from .access import ROLE_OWNER, accessible_documents, can_edit, can_manage, notify_access_changed, role_for
from .activity import log_activity, person
from .models import ActivityLog, Document, DocumentAccess, DocumentVersion
from .permissions import DocumentRolePermission
from .serializers import (
    ActivitySerializer,
    AddMemberSerializer,
    ChangeRoleSerializer,
    DocumentSerializer,
    MemberSerializer,
    MemberUserSerializer,
    VersionDetailSerializer,
    VersionSerializer,
)


class DocumentPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50


class DocumentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET    /api/documents/            list    (?scope=owned|shared, ?search=, ?page=)
    POST   /api/documents/            create            {title?}
    GET    /api/documents/<id>/       retrieve          (any role)
    PATCH  /api/documents/<id>/       rename {title}    (owner, editor)
    DELETE /api/documents/<id>/       delete            (owner)

    Security: the queryset only contains documents the user may open, so a
    request for any other document returns 404 (it does not even reveal that
    the document exists). DocumentRolePermission then checks the role.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, DocumentRolePermission]
    pagination_class = DocumentPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = accessible_documents(user)
        scope = self.request.query_params.get("scope", "")
        if scope == "owned":
            queryset = queryset.filter(owner=user)
        elif scope == "shared":
            queryset = queryset.exclude(owner=user)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search[:100])
        return queryset

    def perform_create(self, serializer):
        document = serializer.save(owner=self.request.user)
        log_activity(document, self.request.user, ActivityLog.CREATED)

    def perform_update(self, serializer):
        old_title = serializer.instance.title
        document = serializer.save()
        if document.title != old_title:
            log_activity(document, self.request.user, ActivityLog.RENAMED, **{"from": old_title, "to": document.title})

    def perform_destroy(self, instance):
        document_id = instance.pk
        instance.delete()
        notify_access_changed(document_id)  # disconnect everyone still editing it


class DocumentMembersMixin:
    permission_classes = [IsAuthenticated]

    def get_document(self, document_pk):
        """404 if the user cannot open the document; then the role decides."""
        document = get_object_or_404(accessible_documents(self.request.user), pk=document_pk)
        self.role = role_for(self.request.user, document)
        return document

    def require_manager(self):
        if not can_manage(self.role):
            raise PermissionDenied("فقط مالك المستند يمكنه إدارة المشاركة.")


class DocumentMembersView(DocumentMembersMixin, APIView):
    """
    GET  /api/documents/<id>/members/   who has access   (owner only)
    POST /api/documents/<id>/members/   share {email, role}  (owner only)
    """

    throttle_scope = "share"

    def get_throttles(self):
        # Limit invitations (each one reveals whether an email is registered).
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get(self, request, document_pk):
        document = self.get_document(document_pk)
        self.require_manager()
        members = document.accesses.select_related("user").order_by("created_at")
        return Response(
            {
                "owner": MemberUserSerializer(document.owner).data,
                "members": MemberSerializer(members, many=True).data,
            }
        )

    def post(self, request, document_pk):
        document = self.get_document(document_pk)
        self.require_manager()
        serializer = AddMemberSerializer(data=request.data, context={"document": document})
        serializer.is_valid(raise_exception=True)
        access = DocumentAccess.objects.create(
            document=document,
            user=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            invited_by=request.user,
        )
        log_activity(document, request.user, ActivityLog.SHARED, target=person(access.user), role=access.role)
        return Response(MemberSerializer(access).data, status=status.HTTP_201_CREATED)


class DocumentMemberDetailView(DocumentMembersMixin, APIView):
    """
    PATCH  /api/documents/<id>/members/<member_id>/  change role {role}  (owner)
    DELETE /api/documents/<id>/members/<member_id>/  remove access       (owner, or the member to leave)
    """

    def get_access(self, document_pk, member_pk):
        document = self.get_document(document_pk)
        return get_object_or_404(DocumentAccess.objects.select_related("user"), pk=member_pk, document=document)

    def patch(self, request, document_pk, member_pk):
        access = self.get_access(document_pk, member_pk)
        self.require_manager()
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if access.role != serializer.validated_data["role"]:
            old_role, access.role = access.role, serializer.validated_data["role"]
            access.save(update_fields=["role"])
            log_activity(
                access.document,
                request.user,
                ActivityLog.ROLE_CHANGED,
                target=person(access.user),
                **{"from": old_role, "to": access.role},
            )
            notify_access_changed(access.document_id, access.user_id)
        return Response(MemberSerializer(access).data)

    def delete(self, request, document_pk, member_pk):
        access = self.get_access(document_pk, member_pk)
        leaving = access.user_id == request.user.id
        if not leaving and self.role != ROLE_OWNER:
            raise PermissionDenied("فقط مالك المستند يمكنه إزالة الأعضاء.")
        document_id, user_id = access.document_id, access.user_id
        if leaving:
            log_activity(access.document, request.user, ActivityLog.LEFT)
        else:
            log_activity(access.document, request.user, ActivityLog.UNSHARED, target=person(access.user))
        access.delete()
        notify_access_changed(document_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Sprint 6: activity log and versions ------------------------------------


class ActivityPagination(PageNumberPagination):
    page_size = 30


class DocumentActivityView(DocumentMembersMixin, APIView):
    """GET /api/documents/<id>/activity/   newest first, ?page=   (any role)"""

    def get(self, request, document_pk):
        document = self.get_document(document_pk)
        queryset = document.activity.select_related("actor")
        paginator = ActivityPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ActivitySerializer(page, many=True).data)


def take_snapshot(document, user, label="", kind=DocumentVersion.KIND_MANUAL):
    """Save the CURRENT content (including edits not yet written to the DB)."""
    flush_open_document(document.pk)
    state = Document.objects.filter(pk=document.pk).values_list("yjs_state", flat=True).first()
    if not state:
        raise ValidationError({"detail": "المستند فارغ، لا يوجد ما يمكن حفظه."})
    return DocumentVersion.objects.create(
        document=document, created_by=user, label=label, kind=kind, yjs_state=bytes(state)
    )


class DocumentVersionsView(DocumentMembersMixin, APIView):
    """
    GET  /api/documents/<id>/versions/   list (without content)  (any role)
    POST /api/documents/<id>/versions/   save a snapshot {label?} (owner, editor)
    """

    def get(self, request, document_pk):
        document = self.get_document(document_pk)
        versions = document.versions.select_related("created_by")[:100]
        return Response(VersionSerializer(versions, many=True).data)

    def post(self, request, document_pk):
        document = self.get_document(document_pk)
        if not can_edit(self.role):
            raise PermissionDenied("القارئ لا يمكنه حفظ الإصدارات.")
        serializer = VersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = take_snapshot(document, request.user, label=serializer.validated_data.get("label", ""))
        log_activity(document, request.user, ActivityLog.VERSION_SAVED, version_id=version.pk, label=version.label)
        return Response(VersionSerializer(version).data, status=status.HTTP_201_CREATED)


class DocumentVersionDetailView(DocumentMembersMixin, APIView):
    """GET /api/documents/<id>/versions/<version_id>/   with content (any role)"""

    def get(self, request, document_pk, version_pk):
        document = self.get_document(document_pk)
        version = get_object_or_404(document.versions.select_related("created_by"), pk=version_pk)
        return Response(VersionDetailSerializer(version).data)


class DocumentVersionRestoreView(DocumentMembersMixin, APIView):
    """
    POST /api/documents/<id>/versions/<version_id>/restore/   (owner, editor)

    1. Saves a backup of the current content (so a restore can be undone).
    2. Logs the restore and returns the old version's content.
    The browser then puts that content into the live editor; the change goes
    through the normal real-time path, so everyone sees it and it is saved.
    """

    def post(self, request, document_pk, version_pk):
        document = self.get_document(document_pk)
        if not can_edit(self.role):
            raise PermissionDenied("القارئ لا يمكنه استرجاع الإصدارات.")
        version = get_object_or_404(document.versions, pk=version_pk)
        label = version.label or f"{version.created_at:%Y-%m-%d %H:%M}"
        try:
            backup = take_snapshot(
                document, request.user, label=f"قبل استرجاع «{label}»"[:100], kind=DocumentVersion.KIND_BACKUP
            )
        except ValidationError:
            backup = None  # the document was empty: nothing to back up
        log_activity(document, request.user, ActivityLog.VERSION_RESTORED, version_id=version.pk, label=label)
        return Response(
            {
                "version": VersionDetailSerializer(version).data,
                "backup": VersionSerializer(backup).data if backup else None,
            }
        )
