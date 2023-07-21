from lone_ease.celery import celery_app
from .constants import ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG
from .models_service import UserInformationDbService,UserTransactionInformationDbService

@celery_app.task
def calculate_credit_score(aadhar_id):

    user_transaction_db_service = UserTransactionInformationDbService()
    total_credit = user_transaction_db_service.get_transactions_sum(aadhar_id, "CREDIT")
    total_debit = user_transaction_db_service.get_transactions_sum(aadhar_id, "DEBIT")

    total_credit_amount = int(total_credit["total_amount"])
    total_debit_amount = int(total_debit["total_amount"])

    total_account_balance = total_credit_amount-total_debit_amount
    credit_score = 0
    if total_account_balance <= ACCOUNT_BALANCE_CONFIG["MIN_VALUE"]:
        credit_score = CREDIT_SCORE_CONFIG["MIN_SCORE"]
    elif total_account_balance >= ACCOUNT_BALANCE_CONFIG["MAX_VALUE"]:
        credit_score = CREDIT_SCORE_CONFIG["MAX_SCORE"]
    else:
        balance_change = ACCOUNT_BALANCE_CONFIG["BALANCE_CHANGE"]
        increment = ACCOUNT_BALANCE_CONFIG["INCREMENT"]
        credit_score = (total_account_balance // balance_change) + increment + CREDIT_SCORE_CONFIG["MIN_SCORE"]

    UserInformationDbService().save_credit_score(aadhar_id, credit_score)
