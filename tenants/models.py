"""
Multi-tenancy models for HiveCore.

Provides tenant isolation at the row level using tenant_id field.
"""

import uuid
import secrets
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """Tenant model for multi-tenancy support.

    Each tenant represents an organization or user group with isolated data.
    """

    class Tier(models.TextChoices):
        FREE = 'free', 'Free'
        TEAM = 'team', 'Team'
        BUSINESS = 'business', 'Business'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='Tenant name')
    slug = models.SlugField(unique=True, verbose_name='Unique slug')
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.FREE,
        verbose_name='Subscription tier'
    )

    # API Key for agentscope integration
    api_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='API Key'
    )

    # Quotas
    max_tokens_per_month = models.BigIntegerField(
        default=500000,
        verbose_name='Max tokens per month'
    )
    max_projects = models.IntegerField(
        default=10,
        verbose_name='Max projects'
    )
    max_agents_per_project = models.IntegerField(
        default=10,
        verbose_name='Max agents per project'
    )

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self._generate_api_key()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_api_key():
        """Generate a secure API key."""
        return f"hc_{secrets.token_urlsafe(32)}"

    def regenerate_api_key(self):
        """Regenerate the API key."""
        self.api_key = self._generate_api_key()
        self.save(update_fields=['api_key', 'updated_at'])
        return self.api_key


class TenantUser(models.Model):
    """Association between User and Tenant.

    A user belongs to one tenant (for MVP simplicity).
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_profile'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tenant User'
        verbose_name_plural = 'Tenant Users'

    def __str__(self):
        return f"{self.user.username} @ {self.tenant.name}"

    @property
    def is_admin(self):
        return self.role in (self.Role.OWNER, self.Role.ADMIN)
