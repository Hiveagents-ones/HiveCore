from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import json
from typing import Optional, Dict, Any

class AuditMiddleware:
    """
    审计中间件，记录所有API请求和响应的关键信息
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """
        中间件核心逻辑，记录请求和响应信息
        """
        try:
            # 记录请求信息
            request_info = self._extract_request_info(request)
            
            # 处理请求并获取响应
            response = await call_next(request)
            
            # 记录响应信息
            response_info = self._extract_response_info(response)
            
            # 合并审计日志
            audit_log = {
                **request_info,
                **response_info,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            # 这里可以添加日志存储逻辑，如写入MongoDB或文件
            print(f"[AUDIT LOG] {json.dumps(audit_log)}")
            
            return response
            
        except HTTPException as http_exc:
            # 处理HTTP异常
            error_log = {
                "path": str(request.url),
                "method": request.method,
                "status_code": http_exc.status_code,
                "error": str(http_exc.detail),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            }
            print(f"[AUDIT ERROR] {json.dumps(error_log)}")
            return JSONResponse(
                content={"detail": str(http_exc.detail)},
                status_code=http_exc.status_code
            )
            
        except Exception as exc:
            # 处理其他异常
            error_log = {
                "path": str(request.url),
                "method": request.method,
                "status_code": 500,
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            }
            print(f"[AUDIT ERROR] {json.dumps(error_log)}")
            return JSONResponse(
                content={"detail": "Internal server error"},
                status_code=500
            )
    
    def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """
        提取请求关键信息
        """
        return {
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "params": dict(request.query_params),
            "body": await self._get_request_body(request)
        }
    
    async def _get_request_body(self, request: Request) -> Optional[Dict]:
        """
        获取请求体内容
        """
        try:
            body = await request.json()
            return body if isinstance(body, dict) else {"raw": str(body)}
        except:
            return None
    
    def _extract_response_info(self, response) -> Dict[str, Any]:
        """
        提取响应关键信息
        """
        return {
            "status_code": response.status_code,
            "response_size": len(response.body) if hasattr(response, "body") else 0
        }