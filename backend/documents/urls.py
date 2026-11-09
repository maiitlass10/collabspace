from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import DocumentMemberDetailView, DocumentMembersView, DocumentViewSet

router = SimpleRouter(trailing_slash=True)
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("documents/<uuid:document_pk>/members/", DocumentMembersView.as_view(), name="document-members"),
    path(
        "documents/<uuid:document_pk>/members/<int:member_pk>/",
        DocumentMemberDetailView.as_view(),
        name="document-member-detail",
    ),
] + router.urls
