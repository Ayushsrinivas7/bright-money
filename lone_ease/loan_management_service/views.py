import json
import uuid

from django.http import HttpResponse
from .services.user_registration_service import UserRegistrationService
from .services.loan_application_service import LoanApplicationService
from .services.loan_payment_service import LoanPaymentService
from .services.post_transaction_service import PostTransactionService 
                                    

app_name = "loan_management_service"

def register_user(request):

    if request.method == "POST":
        payload = json.loads(request.body)
        response = UserRegistrationService().register_user(payload)

        response["success"] = "False" if not response.get("data") else "True"
        return HttpResponse(
            json.dumps(response), status=200, content_type="application/json"
        )
    return HttpResponse(status=401)


def apply_loan(request):
    if request.method == "POST":
        payload = json.loads(request.body)
        response = LoanApplicationService().apply_loan(payload)

        response["success"] = "False" if not response.get("data") else "True"
        return HttpResponse(
                json.dumps(response), status=200, content_type="application/json"
            )
    return HttpResponse(status=401)


def make_payment(request):
    if request.method == "POST":
        payload = json.loads(request.body)
        response = LoanPaymentService().make_payment(payload)
        
        response["success"] = "False" if not response.get("data") else "True"
        return HttpResponse(
                json.dumps(response), status=200, content_type="application/json"
            )
    return HttpResponse(status=401)

def get_statement(request):

    if request.method == "GET":
        loan_id = request.GET.get("loan_id")
        loan_id_uuid = uuid.UUID(loan_id)
        response = PostTransactionService().get_transaction_statement(loan_id_uuid)

        response["success"] = "False" if not response.get("data") else "True"
        return HttpResponse(
                json.dumps(response), status=200, content_type="application/json"
            )
    
    return HttpResponse(status=401)


