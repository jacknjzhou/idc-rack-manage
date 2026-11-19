from rest_framework import viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import Device
from .serializers import DeviceRequestSerializer, DeviceResponseSerializer
from apps.placements.validation import validate_device_update


@extend_schema_view(
    create=extend_schema(request=DeviceRequestSerializer, responses={201: DeviceResponseSerializer},
                         summary="新建设备", tags=["设备"]),
    update=extend_schema(request=DeviceRequestSerializer, responses={200: DeviceResponseSerializer},
                         summary="更新设备", tags=["设备"]),
    partial_update=extend_schema(request=DeviceRequestSerializer, responses={200: DeviceResponseSerializer},
                                 summary="部分更新设备", tags=["设备"]),
    list=extend_schema(responses={200: DeviceResponseSerializer(many=True)}, tags=["设备"]),
    retrieve=extend_schema(responses={200: DeviceResponseSerializer}, tags=["设备"]),
    destroy=extend_schema(tags=["设备"]),
)
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all().order_by("id")
    serializer_class = DeviceResponseSerializer

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DeviceRequestSerializer
        return DeviceResponseSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = Device.objects.create(**s.validated_data)
        return Response(DeviceResponseSerializer(obj).data, status=201)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = self.get_serializer(data=request.data, partial=False)
        s.instance = obj  # UniqueValidator 校验时排除自身，允许保持原 asset_no
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_device_update(obj, d.get("power_w", obj.power_w),
                                   d.get("weight_kg", obj.weight_kg))
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        for k, v in d.items():
            setattr(obj, k, v)
        obj.save()
        return Response(DeviceResponseSerializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = self.get_serializer(data=request.data, partial=True)
        s.instance = obj  # UniqueValidator 校验时排除自身，允许保持原 asset_no
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_device_update(obj, d.get("power_w", obj.power_w),
                                   d.get("weight_kg", obj.weight_kg))
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        for k, v in d.items():
            setattr(obj, k, v)
        obj.save()
        return Response(DeviceResponseSerializer(obj).data)
