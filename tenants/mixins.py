"""
Tenant-aware mixins for models and viewsets.
"""

from django.db import models


class TenantModelMixin(models.Model):
    """Abstract mixin that adds tenant field to models.

    All models that need tenant isolation should inherit from this mixin.

    Usage::

        class Project(TenantModelMixin):
            name = models.CharField(max_length=200)
            # ...
    """

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Tenant'
    )

    class Meta:
        abstract = True


class TenantQuerySetMixin:
    """Mixin for ViewSets to auto-filter by tenant.

    Automatically filters queryset by the current request's tenant
    and sets tenant on create.

    Usage::

        class ProjectViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
            queryset = Project.objects.all()
            serializer_class = ProjectSerializer
    """

    def get_queryset(self):
        """Filter queryset by current tenant."""
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()

    def perform_create(self, serializer):
        """Set tenant on create."""
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            serializer.save(tenant=tenant)
        else:
            serializer.save()


class ProjectTenantQuerySetMixin:
    """Mixin for ViewSets to auto-filter by project's tenant.

    For models that have a 'project' ForeignKey field, this mixin
    filters the queryset by the project's tenant.

    Also includes records where project is NULL (for resources not yet
    assigned to a project).

    Usage::

        class TaskViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
            queryset = Task.objects.all()
            serializer_class = TaskSerializer
    """

    # Override this if the FK to Project has a different name
    project_field_name = 'project'

    def get_queryset(self):
        """Filter queryset by project's tenant.

        Includes records where:
        1. project.tenant matches request tenant, OR
        2. project is NULL (not yet assigned)
        """
        from django.db.models import Q

        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            filter_kwargs = {f'{self.project_field_name}__tenant': tenant}
            null_project_kwargs = {f'{self.project_field_name}__isnull': True}
            return qs.filter(Q(**filter_kwargs) | Q(**null_project_kwargs))
        return qs.none()
