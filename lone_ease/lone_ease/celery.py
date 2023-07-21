import os
from celery import Celery
  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loan_ease.settings')
  
celery_app = Celery('lone_ease')

celery_app.config_from_object('django.conf:settings',
                       namespace='CELERY')
  

celery_app.autodiscover_tasks()