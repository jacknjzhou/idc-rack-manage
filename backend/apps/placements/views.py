from datetime import datetime, timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Placement
from .serializers import PlaceRequestSerializer, MoveRequestSerializer, PlacementResponseSerializer
from .validation import validate_placement

@extend_schema_view(
    create=extend_schema(request=PlaceRequestSerializer, responses={201: PlacementResponseSerializer},
                         summary="设备上架", tags=["放置"]),
    list=extend_schema(responses={200: PlacementResponseSerializer(many=True)}, tags=["放置"]),
    retrieve=extend_schema(responses={200: PlacementResponseSerializer}, tags=["放置"]),
)
class PlacementViewSet(viewsets.ModelViewSet):
    queryset = Placement.objects.all().order_by("-placed_at")
    serializer_class = PlacementResponseSerializer

    def create(self, request, *args, **kwargs):
        s = PlaceRequestSerializer(data=request.data); s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_placement(d["rack"], d["face"], d["start_u"], d["u_size"],
                               d["device"].power_w, d["device"].weight_kg)
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        obj = Placement.objects.create(
            device=d["device"], rack=d["rack"], face=d["face"],
            start_u=d["start_u"], u_size=d["u_size"], status="active")
        return Response(PlacementResponseSerializer(obj).data, status=201)

    @extend_schema(request=None, responses={200: PlacementResponseSerializer},
                   summary="设备下架", tags=["放置"])
    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        p = self.get_object()
        p.status = "removed"
        p.removed_at = datetime.now(timezone.utc)
        p.save(update_fields=["status", "removed_at"])
        return Response(PlacementResponseSerializer(p).data)

    @extend_schema(request=MoveRequestSerializer, responses={200: PlacementResponseSerializer},
                   summary="设备移位", tags=["放置"])
    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        p = self.get_object()
        s = MoveRequestSerializer(data=request.data); s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_placement(d["rack"], d["face"], d["start_u"], p.u_size,
                               p.device.power_w, p.device.weight_kg, exclude_id=p.id)
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        p.rack = d["rack"]; p.face = d["face"]; p.start_u = d["start_u"]
        p.save(update_fields=["rack", "face", "start_u"])
        return Response(PlacementResponseSerializer(p).data)
