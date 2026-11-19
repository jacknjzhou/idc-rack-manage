from rest_framework import viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models import Room
from .serializers import RoomRequestSerializer, RoomResponseSerializer

@extend_schema_view(
    create=extend_schema(request=RoomRequestSerializer, responses={201: RoomResponseSerializer},
                         summary="新建机房", tags=["机房"]),
    update=extend_schema(request=RoomRequestSerializer, responses={200: RoomResponseSerializer},
                         summary="更新机房", tags=["机房"]),
    partial_update=extend_schema(request=RoomRequestSerializer, responses={200: RoomResponseSerializer},
                                 summary="部分更新机房", tags=["机房"]),
    list=extend_schema(responses={200: RoomResponseSerializer(many=True)}, tags=["机房"]),
    retrieve=extend_schema(responses={200: RoomResponseSerializer}, tags=["机房"]),
)
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by("id")
    serializer_class = RoomResponseSerializer   # 响应 Schema

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RoomRequestSerializer        # 请求 Schema（入参校验）
        return RoomResponseSerializer

    def create(self, request, *args, **kwargs):
        # RequestSerializer 校验通过后，用其 validated_data 建对象；响应以 ResponseSerializer 渲染
        s = self.get_serializer(data=request.data); s.is_valid(raise_exception=True)
        obj = Room.objects.create(**s.validated_data)
        return Response(RoomResponseSerializer(obj).data, status=201)

    def update(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, partial=False); s.is_valid(raise_exception=True)
        obj = self.get_object()
        for k, v in s.validated_data.items(): setattr(obj, k, v)
        obj.save()
        return Response(RoomResponseSerializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, partial=True); s.is_valid(raise_exception=True)
        obj = self.get_object()
        for k, v in s.validated_data.items(): setattr(obj, k, v)
        obj.save()
        return Response(RoomResponseSerializer(obj).data)
