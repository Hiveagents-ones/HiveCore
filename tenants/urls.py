"""
Tenant URL configuration.
"""

from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('', views.TenantDetailView.as_view(), name='detail'),
    path('api-key/', views.APIKeyView.as_view(), name='api-key'),
    path('quota/', views.QuotaView.as_view(), name='quota'),
]
