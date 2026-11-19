from rest_framework.routers import DefaultRouter
from .views import RackViewSet

router = DefaultRouter()
router.register("racks", RackViewSet, basename="rack")
urlpatterns = router.urls
