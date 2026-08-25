import os
from celery import Celery

# Django settings module set karein
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

app = Celery("crm")

# Django settings se CELERY_ namespace wale config load karein
app.config_from_object("django.conf:settings", namespace="CELERY")

# Saare apps mein tasks.py automatically discover karein
app.autodiscover_tasks()
