"""
Tenant serializers.
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Tenant, TenantUser


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model."""

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'tier',
            'max_tokens_per_month', 'max_projects', 'max_agents_per_project',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TenantDetailSerializer(TenantSerializer):
    """Serializer with API key (for admins only)."""

    class Meta(TenantSerializer.Meta):
        fields = TenantSerializer.Meta.fields + ['api_key']
        read_only_fields = TenantSerializer.Meta.read_only_fields + ['api_key']


class TenantUserSerializer(serializers.ModelSerializer):
    """Serializer for TenantUser."""

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TenantUser
        fields = ['id', 'username', 'email', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class QuotaSerializer(serializers.Serializer):
    """Serializer for quota information."""

    tokens = serializers.DictField()
    projects = serializers.DictField()
    storage = serializers.DictField()
