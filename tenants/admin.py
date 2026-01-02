from django.contrib import admin
from .models import Tenant, TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'tier', 'is_active', 'created_at']
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'slug']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'tier')
        }),
        ('API Access', {
            'fields': ('api_key',),
            'classes': ('collapse',)
        }),
        ('Quotas', {
            'fields': ('max_tokens_per_month', 'max_projects', 'max_agents_per_project')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'joined_at']
    list_filter = ['role', 'tenant']
    search_fields = ['user__username', 'tenant__name']
    raw_id_fields = ['user', 'tenant']
