import json
import uuid

from django.shortcuts import render
from django.db.models import Sum
from django.http import HttpResponse
from loan_management_service.models import UserInformation, UserTransactionInformation
from loan_management_service.config import ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG

app_name = "loan_management_service"
# Create your views here.

def register_user(request):
    
    print(request.method)
    if request.method == "POST":

        payload = json.loads(request.body)
        print(payload)
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # registering a user
        # also check if user already registered
        user = UserInformation.objects.create(name=name, email=email_id, annual_income=annual_income, aadhar_id=aadhar_id)

        # calculating credit score which will be invoked in a celery task further
        user = UserInformation.objects.filter(aadhar_id=11223344).first()
        total_credit = UserTransactionInformation.objects.filter(user_id=user.aadhar_id, transaction_type='CREDIT').aggregate(total_amount=Sum('amount'))
        total_debit =  UserTransactionInformation.objects.filter(user_id=user.aadhar_id, transaction_type='DEBIT').aggregate(total_amount=Sum('amount'))

        total_credit_amount = int(total_credit['total_amount'])
        total_debit_amount = int(total_debit['total_amount'])

        total_account_balance = total_credit_amount-total_debit_amount
        credit_score = 0
        if total_account_balance <= ACCOUNT_BALANCE_CONFIG['MIN_VALUE']: # value to be stored in config
            credit_score = CREDIT_SCORE_CONFIG['MIN_SCORE']
        elif total_account_balance >= ACCOUNT_BALANCE_CONFIG['MAX_VALUE']:
            credit_score = CREDIT_SCORE_CONFIG['MAX_SCORE']
        else:
            balance_change = ACCOUNT_BALANCE_CONFIG['BALANCE_CHANGE']
            increment = ACCOUNT_BALANCE_CONFIG['INCREMENT']
            credit_score = (total_account_balance//balance_change)+increment
        


        ctx = {
            "user_name": user.name,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "total_account_balance":total_account_balance,
            "credit_score": credit_score
        }

        try: 
            return HttpResponse(json.dumps(ctx), status=201, content_type="application/json")
        except Exception as e:
            return HttpResponse(json.dumps({"msg":"some error occured"}, status=400, content_type="application/json"))

    return HttpResponse(status=401)
