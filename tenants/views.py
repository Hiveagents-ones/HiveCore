"""
Tenant views.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import Tenant, TenantUser
from .serializers import TenantSerializer, TenantDetailSerializer, QuotaSerializer


class TenantDetailView(APIView):
    """Get current tenant details."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'No tenant associated with this user'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is admin
        try:
            tenant_user = request.user.tenant_profile
            is_admin = tenant_user.is_admin
        except TenantUser.DoesNotExist:
            is_admin = False

        if is_admin:
            serializer = TenantDetailSerializer(tenant)
        else:
            serializer = TenantSerializer(tenant)

        return Response(serializer.data)


class APIKeyView(APIView):
    """Manage tenant API key."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current API key (admin only)."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'No tenant found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            tenant_user = request.user.tenant_profile
            if not tenant_user.is_admin:
                return Response(
                    {'error': 'Admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'User not associated with tenant'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({'api_key': tenant.api_key})

    def post(self, request):
        """Regenerate API key (admin only)."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'No tenant found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            tenant_user = request.user.tenant_profile
            if not tenant_user.is_admin:
                return Response(
                    {'error': 'Admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'User not associated with tenant'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_key = tenant.regenerate_api_key()
        return Response({'api_key': new_key})


class QuotaView(APIView):
    """Get tenant quota usage."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'No tenant found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calculate token usage this month
        from observability.models import UsageRecord
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)

        token_usage = UsageRecord.objects.filter(
            tenant=tenant,
            timestamp__gte=month_start
        ).aggregate(total=Sum('total_tokens'))['total'] or 0

        # Calculate project count
        from api.models import Project
        project_count = Project.objects.filter(tenant=tenant).count()

        # Calculate storage (simplified - count files)
        from api.models import File
        storage_stats = File.objects.filter(
            project__tenant=tenant
        ).aggregate(
            total_size=Sum('size'),
            file_count=Count('id')
        )

        quota_data = {
            'tokens': {
                'used': token_usage,
                'limit': tenant.max_tokens_per_month,
                'percent': round(token_usage / tenant.max_tokens_per_month * 100, 2) if tenant.max_tokens_per_month else 0
            },
            'projects': {
                'used': project_count,
                'limit': tenant.max_projects,
                'percent': round(project_count / tenant.max_projects * 100, 2) if tenant.max_projects else 0
            },
            'storage': {
                'used_bytes': storage_stats['total_size'] or 0,
                'file_count': storage_stats['file_count'] or 0,
            }
        }

        return Response(quota_data)
