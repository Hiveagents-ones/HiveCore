"""
Social authentication models.

Provides models for storing OAuth social account bindings.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class SocialAccount(models.Model):
    """Social account binding for OAuth login.

    Stores the association between a Django User and their social accounts
    from various OAuth providers (WeChat, QQ, GitHub, etc.).

    Attributes:
        id (`UUID`):
            Primary key using UUID for security.
        user (`User`):
            The Django user this social account belongs to.
        provider (`str`):
            The OAuth provider name (wechat, qq, github, firebase).
        provider_uid (`str`):
            Unique identifier from the OAuth provider.
        union_id (`str`, optional):
            WeChat union ID for cross-application user identification.
        extra_data (`dict`):
            Additional user information from the provider.
        access_token (`str`, optional):
            OAuth access token for API calls.
        refresh_token (`str`, optional):
            OAuth refresh token.
        token_expires_at (`datetime`, optional):
            Token expiration timestamp.
        created_at (`datetime`):
            When the social account was created.
        updated_at (`datetime`):
            When the social account was last updated.
    """

    class Provider(models.TextChoices):
        """Supported OAuth providers."""
        WECHAT = 'wechat', '微信'
        QQ = 'qq', 'QQ'
        GITHUB = 'github', 'GitHub'
        FIREBASE = 'firebase', 'Firebase'  # Reserved for future

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='social_accounts',
        verbose_name='User'
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        verbose_name='OAuth Provider'
    )
    provider_uid = models.CharField(
        max_length=255,
        verbose_name='Provider User ID'
    )
    union_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Union ID (WeChat)'
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Extra Data'
    )
    access_token = models.TextField(
        blank=True,
        null=True,
        verbose_name='Access Token'
    )
    refresh_token = models.TextField(
        blank=True,
        null=True,
        verbose_name='Refresh Token'
    )
    token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Token Expires At'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Social Account'
        verbose_name_plural = 'Social Accounts'
        unique_together = [['provider', 'provider_uid']]
        indexes = [
            models.Index(fields=['provider', 'provider_uid']),
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['union_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_provider_display()}"
