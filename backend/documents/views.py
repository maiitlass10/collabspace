from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import Document
from .permissions import IsDocumentOwner
from .serializers import DocumentSerializer


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
    GET    /api/documents/            list my documents (?search=, ?page=)
    POST   /api/documents/            create            {title?}
    GET    /api/documents/<id>/       retrieve
    PATCH  /api/documents/<id>/       rename            {title}
    DELETE /api/documents/<id>/       delete

    Security: the queryset only contains the current user's documents, so a
    request for someone else's document returns 404 (it does not even reveal
    that the document exists). IsDocumentOwner is a second line of defence.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsDocumentOwner]
    pagination_class = DocumentPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Document.objects.filter(owner=self.request.user).select_related("owner")
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search[:100])
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
