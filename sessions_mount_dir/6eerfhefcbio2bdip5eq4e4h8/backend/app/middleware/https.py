from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    HTTPS强制中间件，确保所有API通信都通过HTTPS进行。
    如果请求不是通过HTTPS发起，则重定向到HTTPS版本。
    """

    def __init__(self, app: ASGIApp, https_port: int = 443):
        super().__init__(app)
        self.https_port = https_port

    async def dispatch(self, request: Request, call_next):
        # 检查请求是否通过HTTPS
        if not self.is_https(request):
            # 构建HTTPS URL
            url = request.url
            https_url = url.replace(scheme="https", netloc=f"{url.hostname}:{self.https_port}")
            return RedirectResponse(url=str(https_url), status_code=301)

        # 继续处理请求
        response = await call_next(request)
        return response

    @staticmethod
    def is_https(request: Request) -> bool:
        """
        检查请求是否通过HTTPS。
        检查以下条件之一:
        1. 请求的scheme是https
        2. 请求头包含X-Forwarded-Proto: https
        3. 请求头包含X-Forwarded-Scheme: https
        """
        if request.url.scheme == "https":
            return True

        # 检查代理服务器转发的HTTPS标识
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
        forwarded_scheme = request.headers.get("X-Forwarded-Scheme", "").lower()

        return forwarded_proto == "https" or forwarded_scheme == "https"
