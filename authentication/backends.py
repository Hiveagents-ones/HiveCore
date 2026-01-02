"""
Authentication backends for HiveCore.

Supports:
1. JWT authentication for users (via djangorestframework-simplejwt)
2. API Key authentication for agentscope integration
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from tenants.models import Tenant, TenantUser


class APIKeyAuthentication(BaseAuthentication):
    """API Key authentication for agentscope integration.

    agentscope sends requests with X-API-Key header.
    This authenticates the request and attaches the tenant.

    Usage::

        # In agentscope
        headers = {'X-API-Key': 'hc_xxxxx'}
        requests.post(url, headers=headers, json=data)
    """

    def authenticate(self, request):
        """Authenticate request using API key."""
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            # No API key provided, let other authenticators handle it
            return None

        if not api_key.startswith('hc_'):
            raise AuthenticationFailed('Invalid API key format')

        try:
            tenant = Tenant.objects.get(api_key=api_key, is_active=True)
        except Tenant.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')

        # Attach tenant to request
        request.tenant = tenant

        # Return None for user (no user, just tenant)
        # The second element is the auth info
        return (None, {'tenant': tenant, 'auth_type': 'api_key'})

    def authenticate_header(self, request):
        """Return string for WWW-Authenticate header."""
        return 'API-Key'


class TenantJWTAuthentication:
    """JWT authentication that also attaches tenant.

    Wraps the standard JWT authentication and adds tenant lookup.

    Usage::

        REST_FRAMEWORK = {
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'authentication.backends.TenantJWTAuthentication',
                'authentication.backends.APIKeyAuthentication',
            ],
        }
    """

    def __init__(self):
        # Lazy import to avoid circular imports
        from rest_framework_simplejwt.authentication import JWTAuthentication
        self._jwt_auth = JWTAuthentication()

    def authenticate(self, request):
        """Authenticate and attach tenant."""
        result = self._jwt_auth.authenticate(request)

        if result is None:
            return None

        user, token = result

        # Get tenant from user's profile
        try:
            tenant_profile = user.tenant_profile
            request.tenant = tenant_profile.tenant
        except TenantUser.DoesNotExist:
            # User exists but has no tenant
            request.tenant = None

        return (user, token)

    def authenticate_header(self, request):
        """Return string for WWW-Authenticate header."""
        return self._jwt_auth.authenticate_header(request)


# For compatibility, create a class that can be used directly
class JWTAuthenticationWithTenant(BaseAuthentication):
    """JWT authentication with tenant support.

    This is a proper DRF authentication class that wraps simplejwt.
    """

    def authenticate(self, request):
        """Authenticate using JWT and attach tenant."""
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
        except ImportError:
            return None

        jwt_auth = JWTAuthentication()
        result = jwt_auth.authenticate(request)

        if result is None:
            return None

        user, token = result

        # Get tenant from user's profile
        try:
            tenant_profile = user.tenant_profile
            request.tenant = tenant_profile.tenant
        except TenantUser.DoesNotExist:
            request.tenant = None

        return (user, token)

    def authenticate_header(self, request):
        """Return string for WWW-Authenticate header."""
        return 'Bearer'
