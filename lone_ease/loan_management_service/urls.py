from django.urls import path

from loan_management_service.views import register_user

urlpatterns = [path("register_user/", register_user, name="register_user")]
