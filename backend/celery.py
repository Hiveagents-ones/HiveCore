# -*- coding: utf-8 -*-
"""Celery configuration for HiveCore backend."""
# Gevent monkey patching - MUST be before any other imports
import os
if os.environ.get('CELERY_WORKER_POOL') == 'gevent':
    from gevent import monkey
    monkey.patch_all()

from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Create Celery app
app = Celery('backend')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
