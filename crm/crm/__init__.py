try:
    from .celery import app as celery_app
except ImportError:
    # Celery is optional at runtime; management commands and tests must work
    # without the package installed. Install `celery` to enable background
    # task processing.
    celery_app = None

__all__ = ("celery_app",)
