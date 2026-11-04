from rest_framework.routers import SimpleRouter

from .views import DocumentViewSet

router = SimpleRouter(trailing_slash=True)
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
