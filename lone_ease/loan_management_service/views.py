import json

from django.http import HttpResponse
from .services.loan_application_service import (LoanApplicationService,
                                                UserRegistrationService,
                                                LoanPaymentService,
                                                UserRegistrationService,
                                                PostTransactionService)

app_name = "loan_management_service"

# Create your views here.
def register_user(request):
    print(request.method)
    if request.method == "POST":
        payload = json.loads(request.body)
        response = UserRegistrationService().register_user(payload)

        if not response.get('data'):
            pass
        try:
            return HttpResponse(
                json.dumps(response), status=201, content_type="application/json"
            )
        except Exception as e:
            print(f"ERROR is {e}")
            return HttpResponse(
                json.dumps({"msg": "some error occured"}),
                status=400,
                content_type="application/json",
            )

    return HttpResponse(status=401)


def apply_loan(request):
    if request.method == "POST":
        payload = json.loadds(request.body)
        response = LoanApplicationService().apply_loan(payload)
        if not response.get("data"):
            response = response["data"]
            return HttpResponse(
                json.dumps(response), status=201, content_type="application/json"
            )
        else:
            pass
    return HttpResponse(status=401)


def make_payment(request):
    if request.method == "POST":
        payload = json.loads(request.body)
        response = LoanPaymentService().make_payment(payload)
        if not response.get("data"):
            response = response["data"]
            return HttpResponse(
                json.dumps(response), status=201, content_type="application/json"
            )
        else:
            pass

def get_statement(request, loan_id):
    """
    past_transactions :
    1. get_all_entries against the loan_id where amount_paid is not zero and extract date, principal, interest, amount_paid

    upcoming_transactions :
    1. get_all_entries against the loan_id where amount_paid is zero and eextract their amount_due and due_date

    """
    # Past Transactions
    if request.method == "GET":
        
        response = PostTransactionService().get_transaction_statement(loan_id)
        if not response.get('data'):
            pass


