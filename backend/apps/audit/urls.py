from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

router = DefaultRouter()
router.register("auditlog", AuditLogViewSet, basename="auditlog")
urlpatterns = router.urls
