"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from execution.views import (
    ProjectExecuteView,
    SuggestAgentsView,
    GenerateAvatarsView,
    RankAgentsView,
    CreateMetasoAgentView,
)


def health_check(request):
    """Health check endpoint for ALB."""
    return JsonResponse({"status": "healthy"})


def celery_debug(request):
    """Debug endpoint to check Celery configuration."""
    from backend.celery import app
    from django.conf import settings

    result = {
        "celery_broker_url": settings.CELERY_BROKER_URL[:50] + "..." if settings.CELERY_BROKER_URL else None,
        "celery_result_backend": settings.CELERY_RESULT_BACKEND[:50] + "..." if settings.CELERY_RESULT_BACKEND else None,
        "redis_url_env": bool(settings.REDIS_URL),
    }

    # Try to ping Redis
    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        result["redis_ping"] = "success"
    except Exception as e:
        result["redis_ping"] = f"failed: {str(e)}"

    # Try to send a test task
    try:
        from backend.celery import debug_task
        task_result = debug_task.delay()
        result["test_task_id"] = task_result.id
        result["test_task_state"] = task_result.state
    except Exception as e:
        result["test_task_error"] = str(e)

    return JsonResponse(result)


urlpatterns = [
    # Health check (must be before other routes)
    path('api/health/', health_check, name='health-check'),
    path('api/celery-debug/', celery_debug, name='celery-debug'),
    path('admin/', admin.site.urls),
    # Explicit API endpoints (must be before includes to avoid router conflicts)
    path('api/v1/agents/generate-avatars/', GenerateAvatarsView.as_view(), name='agents-generate-avatars'),
    path('api/v1/projects/<int:project_id>/execute/', ProjectExecuteView.as_view(), name='project-execute'),
    path('api/v1/projects/<int:project_id>/suggest-agents/', SuggestAgentsView.as_view(), name='project-suggest-agents'),
    path('api/v1/projects/<int:project_id>/rank-agents/', RankAgentsView.as_view(), name='project-rank-agents'),
    path('api/v1/agents/create-metaso/', CreateMetasoAgentView.as_view(), name='agents-create-metaso'),
    # API endpoints (includes with routers)
    path('api/v1/', include('api.urls')),
    path('api/v1/tenant/', include('tenants.urls')),
    path('api/v1/observability/', include('observability.urls')),
    path('api/v1/execution/', include('execution.urls')),
    # JWT authentication endpoints
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # OAuth authentication endpoints
    path('api/v1/auth/oauth/', include('authentication.urls')),
    # Swagger/OpenAPI documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
