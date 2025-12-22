from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    HTTPS强制跳转中间件
    确保所有支付请求使用加密传输
    """

    def __init__(self, app, https_only: bool = True):
        super().__init__(app)
        self.https_only = https_only
        # 在生产环境中强制HTTPS
        self.is_production = os.getenv("ENVIRONMENT", "development") == "production"

    async def dispatch(self, request: Request, call_next):
        # 检查是否需要强制HTTPS
        if self.https_only and self.is_production:
            # 检查是否已经是HTTPS请求
            if request.url.scheme != "https":
                # 检查是否是支付相关请求
                if self.is_payment_related(request):
                    # 构建HTTPS URL
                    https_url = request.url.replace(scheme="https")
                    return RedirectResponse(url=str(https_url), status_code=301)

        # 对于非支付请求或开发环境，继续正常处理
        response = await call_next(request)
        return response

    def is_payment_related(self, request: Request) -> bool:
        """
        判断请求是否与支付相关
        """
        # 检查URL路径
        payment_paths = ["/api/v1/payments", "/api/v1/renew", "/api/v1/subscription"]
        if any(request.url.path.startswith(path) for path in payment_paths):
            return True

        # 检查请求头中的敏感信息
        sensitive_headers = ["authorization", "credit-card", "payment"]
        for header in sensitive_headers:
            if header in request.headers:
                return True

        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件
    添加必要的安全响应头
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 添加安全头
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        return response