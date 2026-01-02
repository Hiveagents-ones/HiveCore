# -*- coding: utf-8 -*-
"""Backend package initialization.

This module loads the Celery app when Django starts.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
