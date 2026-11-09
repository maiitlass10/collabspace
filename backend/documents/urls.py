from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    DocumentActivityView,
    DocumentMemberDetailView,
    DocumentMembersView,
    DocumentVersionDetailView,
    DocumentVersionRestoreView,
    DocumentVersionsView,
    DocumentViewSet,
)

router = SimpleRouter(trailing_slash=True)
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("documents/<uuid:document_pk>/members/", DocumentMembersView.as_view(), name="document-members"),
    path(
        "documents/<uuid:document_pk>/members/<int:member_pk>/",
        DocumentMemberDetailView.as_view(),
        name="document-member-detail",
    ),
    path("documents/<uuid:document_pk>/activity/", DocumentActivityView.as_view(), name="document-activity"),
    path("documents/<uuid:document_pk>/versions/", DocumentVersionsView.as_view(), name="document-versions"),
    path(
        "documents/<uuid:document_pk>/versions/<int:version_pk>/",
        DocumentVersionDetailView.as_view(),
        name="document-version-detail",
    ),
    path(
        "documents/<uuid:document_pk>/versions/<int:version_pk>/restore/",
        DocumentVersionRestoreView.as_view(),
        name="document-version-restore",
    ),
] + router.urls
