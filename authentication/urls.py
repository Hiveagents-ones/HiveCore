"""
OAuth authentication URL configuration.

Provides URL patterns for OAuth authorization and callback endpoints.
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # OAuth authorization - Get authorization URL
    path(
        'wechat/authorize/',
        views.WeChatAuthorizeView.as_view(),
        name='wechat-authorize'
    ),
    path(
        'qq/authorize/',
        views.QQAuthorizeView.as_view(),
        name='qq-authorize'
    ),
    path(
        'github/authorize/',
        views.GitHubAuthorizeView.as_view(),
        name='github-authorize'
    ),

    # OAuth callbacks - Handle provider callbacks
    path(
        'wechat/callback/',
        views.WeChatCallbackView.as_view(),
        name='wechat-callback'
    ),
    path(
        'qq/callback/',
        views.QQCallbackView.as_view(),
        name='qq-callback'
    ),
    path(
        'github/callback/',
        views.GitHubCallbackView.as_view(),
        name='github-callback'
    ),

    # Social account management
    path(
        'accounts/',
        views.SocialAccountListView.as_view(),
        name='accounts'
    ),
    path(
        'unbind/<str:provider>/',
        views.SocialAccountUnbindView.as_view(),
        name='unbind'
    ),

    # Phone login
    path(
        'phone/login/',
        views.PhoneLoginView.as_view(),
        name='phone-login'
    ),
    path(
        'phone/send-code/',
        views.SendVerificationCodeView.as_view(),
        name='phone-send-code'
    ),
]
