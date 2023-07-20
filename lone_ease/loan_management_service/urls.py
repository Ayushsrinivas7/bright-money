from django.urls import path

from loan_management_service.views import register_user,apply_loan, make_payment, get_statement

urlpatterns = [
    path("register_user/", register_user, name="register_user"),
    path("apply_loan/", apply_loan, name="apply_loan"),
    path("make_payment/", make_payment, name="make_payment"),
    path("get_statement/<str:loan_id>/", get_statement, name="get_statement")
]
