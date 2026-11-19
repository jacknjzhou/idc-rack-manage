from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    """统一错误响应：{code, message, fields}。"""
    if isinstance(exc, ProtectedError):
        return Response({"code": "protected_error", "message": "存在关联记录，无法删除", "fields": []},
                        status=status.HTTP_409_CONFLICT)
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        payload = {"code": "error", "message": str(data["detail"]), "fields": {}}
    else:
        payload = {"code": "validation_error", "message": "参数校验失败", "fields": data}
    response.data = payload
    return response
