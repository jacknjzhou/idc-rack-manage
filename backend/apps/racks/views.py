from rest_framework import viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models import Rack
from .serializers import RackRequestSerializer, RackResponseSerializer


@extend_schema_view(
    create=extend_schema(request=RackRequestSerializer, responses={201: RackResponseSerializer},
                         summary="新建机柜", tags=["机柜"]),
    update=extend_schema(request=RackRequestSerializer, responses={200: RackResponseSerializer},
                         summary="更新机柜", tags=["机柜"]),
    partial_update=extend_schema(request=RackRequestSerializer, responses={200: RackResponseSerializer},
                                 summary="部分更新机柜", tags=["机柜"]),
    list=extend_schema(responses={200: RackResponseSerializer(many=True)}, tags=["机柜"]),
    retrieve=extend_schema(responses={200: RackResponseSerializer}, tags=["机柜"]),
)
class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.all().order_by("id")
    serializer_class = RackResponseSerializer   # 响应 Schema

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RackRequestSerializer        # 请求 Schema（入参校验）
        return RackResponseSerializer

    def create(self, request, *args, **kwargs):
        # RequestSerializer 校验通过后，用其 validated_data 建对象；响应以 ResponseSerializer 渲染
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = Rack.objects.create(**s.validated_data)
        return Response(RackResponseSerializer(obj).data, status=201)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = self.get_serializer(data=request.data, partial=False)
        s.instance = obj  # UniqueValidator 校验时排除自身，允许保持原 location_code
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            setattr(obj, k, v)
        obj.save()
        return Response(RackResponseSerializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = self.get_serializer(data=request.data, partial=True)
        s.instance = obj  # UniqueValidator 校验时排除自身，允许保持原 location_code
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            setattr(obj, k, v)
        obj.save()
        return Response(RackResponseSerializer(obj).data)
