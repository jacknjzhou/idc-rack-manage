"""把当前请求放进 threadlocal，供审计信号在视图内取用当前用户。

注意：DRF 的认证发生在 view dispatch 期间，晚于中间件入口，
所以这里保存 request 对象本身，信号触发时（视图内）再解析 request.user。
"""
import threading

_local = threading.local()


class CurrentUserMiddleware:
    """保存当前请求，供 get_current_user() 解析出请求用户。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


def get_current_user():
    """当前请求用户；请求外返回 None，匿名请求返回 None。"""
    request = getattr(_local, "request", None)
    if request is None:
        return None
    u = getattr(request, "user", None)
    if u is not None and getattr(u, "is_authenticated", False):
        return u
    return None
