import json
import uuid

from datetime import datetime,timedelta
from django.shortcuts import render
from django.db.models import Sum
from django.http import HttpResponse
from loan_management_service.models import UserInformation, UserTransactionInformation, LoanInfo, EMIDetails
from loan_management_service.constants import ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG, SUPPORTED_LOAN_TYPES, LOAN_BOUNDS, USER_INCOME_FOR_LOAN

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
            "user_uuid": user.uuid,
            "user_name": user.name,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "total_account_balance":total_account_balance,
            "credit_score": credit_score
        }

        try: 
            return HttpResponse(json.dumps(ctx), status=201, content_type="application/json")
        except Exception as e:
            print(f"ERROR is {e}")
            return HttpResponse(json.dumps({"msg":"some error occured"}), status=400, content_type="application/json")

    return HttpResponse(status=401)


def apply_loan(request):

    if request.method == "POST":

        payload = json.loads(request.body)
        user_uuid = payload.get('user_uuid')
        loan_type = payload.get('loan_type')
        loan_amount = payload.get('loan_amount')
        interest_rate = payload.get('interest_rate')
        term_period = payload.get('term_period')
        disbursement_date = payload.get('disbursement_date')


        if loan_type not in SUPPORTED_LOAN_TYPES:
            message = {'msg': 'loan type not found'}

        loan_bound_amount = LOAN_BOUNDS[loan_type]
        if loan_amount > loan_bound_amount:
            message = {'msg': 'loan amount out of bounds'}
        
        user = UserInformation.objects.filter(user_uuid=user_uuid).first()

        if user is None:
            message = {'msg': 'user not registered'}

        if user.annual_income >= USER_INCOME_FOR_LOAN:
            message = {'msg': 'annual income below threshold to apply for loan'}

        if interest_rate <= 14:
            message = {'msg': 'interest rate below threshold'}
    
        interest = (principal_amount*interest_rate*term_period)/100

        if interest < 10000:  
            message = {'msg': 'low interest'}
        
        principal_amount = loan_amount
        monthly_rate = interest_rate/12
        n = term_period-1
        emi = get_emi_for_loan(None, principal_amount, monthly_rate, n)

        monthly_income = user.annual_income//12
        emi_threshold = 0.06*monthly_income

        if emi > emi_threshold:
            message = {'msg': 'interest rate below threshold'}

        loan_details = LoanInfo.objects.create(user_uuid=user.user_uuid, loan_type=loan_type, loan_amount=loan_amount, 
                                                annual_interest_rate=interest_rate, term_period=term_period, disbursement_date=disbursement_date)

        save_emi_details(loan_details.id, emi,disbursement_date, term_period)

        loan_id = loan_details.id
        emi_details_objects = EMIDetails.objects.filter(loan_id=loan_details.id).all()

        for emi_details in emi_details_objects:
            pass
            #make a dictionary of all the values for due amount and installment date
    

    def save_emi_details(loan_id, emi, disbursement_date, term_period):

        emi_models = []
        for i in range(term_period):
            installment_date = disbursement_date+timedelta()
            emi_model = EMIDetails(loan_id=loan_id, amount_due=emi, installment_date=installment_date)
            emi_models.append(emi_model)

        EMIDetails.bulk_create(emi_models)
    

    def get_emi_for_loan(loan_id, principal_amount, monthly_rate, term_period):

        if loan_id is None:
            return (principal_amount*monthly_rate*(1+monthly_rate)**term_period)/((1+monthly_rate)**term_period-1)
        else:
            pass

    def make_payment(request):

        if request.method == "POST":

            payload = json.loads(request.body)
            loan_id = payload.get('loan_id')
            amount = payload.get('amount')

            loan_info = LoanInfo.objects.filter(loan_id=loan_id).first()
            if not loan_info:
                # loan does not exist
                pass

            datetime_obj = 0
            emi_info = EMIDetails.objects.filter(loan_id=loan_info.id, installment_date=datetime_obj).first()
            if emi_info.amount_due>0 and emi_info.amount_paid>0:
                #emi has been paid for this month
                pass

            if amount == emi_info.amount_due:
                # update the amount_paid to amount_due
                pass
            else:
                # recalculate the emi's for the next months
                # calculate the interest and principal amount
                # update emi for every entry after the current entry
                # if emi's due are zero update the amount_due to 0 for the next entries
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
                message = {'msg': 'no loan has been applied'}

            past_transactions = LoanInfo.objects.filter(loan_id=loan_info.id, amount_due__gt=0, amount_paid__gt=0).values()

            upcoming_transactions = LoanInfo.objects.filter(loan_id=loan_info.id, amount_due__gt=0, amount_paid=0).values()

