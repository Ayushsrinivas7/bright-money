from ..models_service import UserInformationDbService, UserTransactionInformationDbService
from ..constants import ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG

class UserRegistrationService:
    def __init__(self):
        self.user_information_db_service = UserInformationDbService()
        self.user_transaction_db_service = UserTransactionInformationDbService()

    def register_user(self, payload):
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # registering a user
        is_user_exist = self.user_information_db_service.get_user_by_aadhar(aadhar_id)
        if is_user_exist:
            return {'message': 'User already exists'}
        # also check if user already registered
        user = self.user_information_db_service.create_user(name, email_id, annual_income, aadhar_id)

        # calculating credit score which will be invoked in a celery task further
        response = self.calculate_credit_score(user.aadhar_id)
        if response.get('message'):
            return {
                'message': 'user successfully registered',
                'data': {
                    'user_uuid': user.user_uuid
                }}
        else:
            return {'message': 'Not able to calculate credit score'}
        
    def calculate_credit_score(self, aadhar_id):


        total_credit = self.user_transaction_db_service.get_transactions_sum(aadhar_id, "CREDIT")
        total_debit = self.user_transaction_db_service.get_transactions_sum(aadhar_id, "DEBIT")

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
            credit_score = (total_account_balance // balance_change) + increment
        
        self.user_information_db_service.save_credit_score(aadhar_id, credit_score)

        return {'message': 'credit score calculated and stored'}
