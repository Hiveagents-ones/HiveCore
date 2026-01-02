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


urlpatterns = [
    # Health check (must be before other routes)
    path('api/health/', health_check, name='health-check'),
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
