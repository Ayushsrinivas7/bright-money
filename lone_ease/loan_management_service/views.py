import json
from datetime import timedelta

from django.db.models import Sum
from django.http import HttpResponse

from .constants import (ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG,
                        LOAN_BOUNDS, SUPPORTED_LOAN_TYPES,
                        USER_INCOME_FOR_LOAN)
from .models import (EMIDetails, LoanInfo, UserInformation,
                     UserTransactionInformation)
from .services.loan_application_service import (LoanApplicationService,
                                                LoanPaymentService,
                                                UserRegistrationService)

app_name = "loan_management_service"


# Create your views here.
def register_user(request):
    print(request.method)
    if request.method == "POST":
        payload = json.loads(request.body)
        print(payload)
        response = UserRegistrationService().register_user(payload)
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # registering a user
        # also check if user already registered
        user = UserInformation.objects.create(
            name=name, email=email_id, annual_income=annual_income, aadhar_id=aadhar_id
        )

        # calculating credit score which will be invoked in a celery task further
        user = UserInformation.objects.filter(aadhar_id=11223344).first()
        total_credit = UserTransactionInformation.objects.filter(
            user_id=user.aadhar_id, transaction_type="CREDIT"
        ).aggregate(total_amount=Sum("amount"))
        total_debit = UserTransactionInformation.objects.filter(
            user_id=user.aadhar_id, transaction_type="DEBIT"
        ).aggregate(total_amount=Sum("amount"))

        total_credit_amount = int(total_credit["total_amount"])
        total_debit_amount = int(total_debit["total_amount"])

        total_account_balance = total_credit_amount - total_debit_amount
        credit_score = 0
        if (
            total_account_balance <= ACCOUNT_BALANCE_CONFIG["MIN_VALUE"]
        ):  # value to be stored in config
            credit_score = CREDIT_SCORE_CONFIG["MIN_SCORE"]
        elif total_account_balance >= ACCOUNT_BALANCE_CONFIG["MAX_VALUE"]:
            credit_score = CREDIT_SCORE_CONFIG["MAX_SCORE"]
        else:
            balance_change = ACCOUNT_BALANCE_CONFIG["BALANCE_CHANGE"]
            increment = ACCOUNT_BALANCE_CONFIG["INCREMENT"]
            credit_score = (total_account_balance // balance_change) + increment

        ctx = {
            "user_uuid": user.uuid,
            "user_name": user.name,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "total_account_balance": total_account_balance,
            "credit_score": credit_score,
        }

        try:
            return HttpResponse(
                json.dumps(ctx), status=201, content_type="application/json"
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
        payload = json.loadds(reques.body)
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
        # check whether any loan entry exists against that loan id
        """
        past_transactions :
        1. get_all_entries against the loan_id where amount_paid is not zero and extract date, principal, interest, amount_paid

        upcoming_transactions :
        1. get_all_entries against the loan_id where amount_paid is zero and eextract their amount_due and due_date

        """
        # Past Transactions
        if request.method == "GET":
            loan_info = LoanInfo.objects.filter(loan_id=loan_id).first()
            if loan_info is None:
                message = {"msg": "no loan has been applied"}

            past_transactions = LoanInfo.objects.filter(
                loan_id=loan_info.id, amount_due__gt=0, amount_paid__gt=0
            ).values()

            upcoming_transactions = LoanInfo.objects.filter(
                loan_id=loan_info.id, amount_due__gt=0, amount_paid=0
            ).values()
