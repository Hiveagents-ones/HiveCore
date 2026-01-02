"""
Tenant middleware for request processing.
"""

from django.utils.deprecation import MiddlewareMixin

from .models import Tenant


class TenantMiddleware(MiddlewareMixin):
    """Middleware to attach tenant to request.

    Tenant can be determined from:
    1. Authentication (JWT with tenant info)
    2. API Key header (X-API-Key)
    3. Subdomain (tenant.hivecore.ai)

    The middleware sets request.tenant which can be used by views.
    """

    def process_request(self, request):
        """Process request and attach tenant."""
        # Skip if already set by authentication
        if hasattr(request, 'tenant') and request.tenant:
            return

        # Try API Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            try:
                tenant = Tenant.objects.get(api_key=api_key, is_active=True)
                request.tenant = tenant
                return
            except Tenant.DoesNotExist:
                pass

        # Try subdomain
        host = request.get_host().split(':')[0]
        if '.' in host:
            slug = host.split('.')[0]
            if slug not in ('www', 'api', 'localhost'):
                try:
                    tenant = Tenant.objects.get(slug=slug, is_active=True)
                    request.tenant = tenant
                    return
                except Tenant.DoesNotExist:
                    pass

        # No tenant found
        request.tenant = None
