from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    """统一错误响应：{code, message, fields}。"""
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
