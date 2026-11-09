from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .access import ROLE_OWNER, accessible_documents, can_manage, notify_access_changed, role_for
from .models import DocumentAccess
from .permissions import DocumentRolePermission
from .serializers import (
    AddMemberSerializer,
    ChangeRoleSerializer,
    DocumentSerializer,
    MemberSerializer,
    MemberUserSerializer,
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
        serializer.save(owner=self.request.user)

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
            access.role = serializer.validated_data["role"]
            access.save(update_fields=["role"])
            notify_access_changed(access.document_id, access.user_id)
        return Response(MemberSerializer(access).data)

    def delete(self, request, document_pk, member_pk):
        access = self.get_access(document_pk, member_pk)
        leaving = access.user_id == request.user.id
        if not leaving and self.role != ROLE_OWNER:
            raise PermissionDenied("فقط مالك المستند يمكنه إزالة الأعضاء.")
        document_id, user_id = access.document_id, access.user_id
        access.delete()
        notify_access_changed(document_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
